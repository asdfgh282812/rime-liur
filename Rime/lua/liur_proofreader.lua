-- 短上下文只留在記憶體；Context property 只存不含文字的狀態編號。
local M = {}
local states, next_id = {}, 0
local accepted, noop = 1, 2
local context_options = {
  ascii_mode = true, liur_proofread = true, liur_traditional = true,
  liur_simplified = true, liur_trad_to_simp = true, liur_japanese = true,
  simplification = true,
}

local function chinese(text)
  if text == "" or not utf8.len(text) then return false end
  for _, code in utf8.codes(text) do
    if code < 0x3400 or code > 0x9fff then return false end
  end
  return true
end

local function state_for(context)
  local id = context:get_property("liur_checker_id")
  if id == "" or not states[id] then
    next_id = next_id + 1
    id = tostring(next_id)
    context:set_property("liur_checker_id", id)
    states[id] = { history = "" }
  end
  return states[id], id
end

local function invalidate_hint(state)
  state.hint, state.cached_key, state.cached_result = nil, nil, nil
end

local function clear(state)
  state.history, state.last_activity = "", nil
  invalidate_hint(state)
end

local function enabled(context)
  return context:get_option("liur_proofread") and context:get_option("liur_traditional")
    and not context:get_option("ascii_mode")
end

local function remember(state, text)
  invalidate_hint(state)
  if not chinese(text) then clear(state); return end
  local history = state.history .. text
  local length = utf8.len(history)
  state.history = length > 32 and history:sub(utf8.offset(history, length - 31)) or history
  state.last_activity = os.time()
end

local function shell_quote(value)
  return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function query(env, history, original)
  -- 短文字只經本機子行程參數傳遞，不寫入檔案或日誌。
  -- 不載入 .so，避免原廠鼠鬚管的程式簽章限制。
  local command = "exec " .. shell_quote(env.client) .. " " .. shell_quote(env.socket)
    .. " " .. shell_quote(history) .. " " .. shell_quote(original) .. " 2>/dev/null"
  local ok, pipe = pcall(io.popen, command, "r")
  if not ok or not pipe then return nil end
  -- 空行是「沒有建議」；完全沒回應則是暫時失敗，不能永久快取成無建議。
  local result = pipe:read("*l")
  pipe:close()
  return result
end

M.processor = {
  init = function(env)
    local context = env.engine.context
    env.state, env.id = state_for(context)
    env.context_timeout = env.engine.schema.config:get_int("proofreader/context_timeout") or 120
    clear(env.state)
    env.commit_connection = context.commit_notifier:connect(function(ctx)
      if enabled(ctx) then remember(env.state, ctx:get_commit_text()) else clear(env.state) end
    end)
    env.option_connection = context.option_update_notifier:connect(function(_, name)
      -- 候選視窗方向等前端選項不代表文件內容或游標改變。
      if context_options[name] then clear(env.state) end
    end)
  end,
  func = function(key, env)
    if key:release() then return noop end
    local context, state = env.engine.context, env.state
    local code = key.keycode
    if key:ctrl() or key:alt() or key:super() or not enabled(context) then
      clear(state)
      return noop
    end
    local now = os.time()
    -- 只在開始新組字時檢查閒置；看提示或修改當前字碼不應失去前文。
    if context.input == "" and state.last_activity and now - state.last_activity > env.context_timeout then
      clear(state)
    end
    state.last_activity = now
    local hint = state.hint
    if code == 0xff09 and not key:shift() and hint and context.input == hint.input
        and state.history == hint.history then
      local candidate = context:get_selected_candidate()
      if candidate and candidate.text == hint.original then
        env.engine:commit_text(hint.text)
        remember(state, hint.text)
        context:clear()
        return accepted
      end
    end
    if code == 0xff08 then
      if context.input == "" and state.history ~= "" then
        -- 已上屏的 Backspace 交給文件刪字，同時只回退一個已知中文字。
        state.history = state.history:sub(1, utf8.offset(state.history, -1) - 1)
      end
      -- 組字中的 Backspace 只刪字碼，已上屏的前文保持不變。
      invalidate_hint(state)
    elseif code == 0xff1b and context.input ~= "" then
      invalidate_hint(state)
    elseif context:has_menu() and (code == 0xff52 or code == 0xff54 or code == 0xff55 or code == 0xff56) then
      -- 候選導航沒有改變已上屏文字；Tab 仍會核對目前反白的字。
    elseif code == 0xff09 or code == 0xffff or code == 0xff1b or (code >= 0xff50 and code <= 0xff57) then
      clear(state)
    elseif context.input == "" and (code == 39 or code == 59 or code == 96 or code == 44 or code == 46 or code == 32) then
      clear(state)
    end
    return noop
  end,
  fini = function(env)
    if env.commit_connection then env.commit_connection:disconnect() end
    if env.option_connection then env.option_connection:disconnect() end
    states[env.id] = nil
  end,
}

M.filter = {
  init = function(env)
    local directory = rime_api.get_user_data_dir()
    env.socket = directory .. "/proofreader/run/checker.sock"
    env.codes = ReverseLookup("liur.extended")
    local client = directory .. "/proofreader/liur_proofread_client"
    local file = io.open(client, "rb")
    if file then file:close(); env.client = client end
  end,
  func = function(input, env)
    local context = env.engine.context
    local state = state_for(context)
    state.hint = nil
    local first = true
    for candidate in input:iter() do
      if first and env.client and enabled(context) and state.history ~= ""
          and context.input:match("^[a-z]+$") and utf8.len(candidate.text) == 1 and chinese(candidate.text) then
        local exact = false
        for code in env.codes:lookup(candidate.text):gmatch("%S+") do
          if code:gsub("~", "") == context.input then exact = true; break end
        end
        if exact then
          local cache_key = state.history .. "\t" .. context.input .. "\t" .. candidate.text
          if cache_key ~= state.cached_key then
            local result = query(env, state.history, candidate.text)
            state.cached_key = result ~= nil and cache_key or nil
            state.cached_result = result or ""
          end
          local text, phrase = state.cached_result:match("^([^\t]+)\t([^\t]+)$")
          if text and chinese(text) and utf8.len(text) == 1 and chinese(phrase)
              and utf8.len(phrase) >= 2 and utf8.len(phrase) <= 4
              and (state.history .. text):sub(-#phrase) == phrase then
            state.hint = { text = text, original = candidate.text, input = context.input, history = state.history }
            local comment = candidate.comment ~= "" and candidate.comment .. " " or ""
            candidate = ShadowCandidate(candidate, candidate.type, candidate.text,
              comment .. "建議「" .. text .. "」：" .. phrase .. "〔Tab採用〕")
          end
        end
      end
      first = false
      yield(candidate)
    end
  end,
}

return M
