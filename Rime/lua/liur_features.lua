-- 嘸蝦米的同音字查詢與語言模式。詞庫查詢交給 Rime，不另外複製碼表。
local M = {}
local accepted, noop = 1, 2
local commands = {
  [",,t"] = { "liur_traditional", "繁體中文" },
  [",,c"] = { "liur_simplified", "簡體字碼" },
  [",,ct"] = { "liur_trad_to_simp", "打繁出簡" },
  [",,j"] = { "liur_japanese", "日文" },
}
local options = { "liur_traditional", "liur_simplified", "liur_trad_to_simp", "liur_japanese" }

-- 數字依目前頁面計算；方向鍵選取後，空白使用目前反白的候選字。
local function selected_candidate(context, keycode, config)
  if keycode < 48 or keycode > 57 then
    return context:get_selected_candidate()
  end
  local segment = context.composition:back()
  if not segment then return nil end
  local keys = config:get_string("menu/alternative_select_keys") or "1234567890"
  local position = keys:find(string.char(keycode), 1, true)
  local page_size = config:get_int("menu/page_size") or 5
  if not position or position > page_size then return nil end
  local page_start = math.floor(segment.selected_index / page_size) * page_size
  return segment:get_candidate_at(page_start + position - 1)
end

local function is_selection_key(code)
  return code == 32 or (code >= 48 and code <= 57)
end

M.processor = function(key, env)
  local context = env.engine.context
  if key:release() or key:ctrl() or key:alt() or key:super()
      or context:get_option("ascii_mode") then
    return noop
  end
  local code, input = key.keycode, context.input
  if code == 0xff1b and (input:match("^'[a-z]+$") or input:sub(1, 2) == "'=") then
    context:clear()
    return accepted
  end
  local command = commands[input]
  if command and (code == 32 or code == 0xff0d or code == 48) then
    context:clear()
    -- 避免先前 Ctrl+. 的狀態使日文字形或繁體模式仍被轉簡。
    context:set_option("simplification", false)
    for _, name in ipairs(options) do
      context:set_option(name, name == command[1])
    end
    return accepted
  end

  if input:match("^'[a-z]+$") and is_selection_key(code) then
    local candidate = selected_candidate(context, code, env.engine.schema.config)
    if candidate then
      context:set_property("liur_homophone_query", input)
      context.input = "'=" .. candidate.text
      return accepted
    end
  elseif input:sub(1, 2) == "'=" then
    if code == 0xff08 then -- Backspace：返回選原字階段
      local previous = context:get_property("liur_homophone_query")
      context.input = previous ~= "" and previous or "'"
      return accepted
    end
    if is_selection_key(code) or code == 0xff0d then
      local candidate = selected_candidate(context, code, env.engine.schema.config)
      if candidate then
        env.engine:commit_text(candidate.text)
        context:clear()
      end
      return accepted
    end
    -- 導航交給 Rime；避免字母追加到內部查詢字串。
    if code >= 33 and code <= 126 then return accepted end
  end
  return noop
end

M.segmentor = function(segmentation, env)
  local context = env.engine.context
  local tag
  if context:get_option("liur_japanese") then tag = "liur_japanese"
  elseif context:get_option("liur_simplified") then tag = "liur_simplified"
  else return true end

  local start = segmentation:get_current_start_position()
  local input = segmentation.input:sub(start + 1)
  -- matcher 已處理注音、反查等模式；這裡只接管一般蝦米碼。
  if not input:match("^[a-z%[%],%.]+$") then return true end
  local segment = Segment(start, #segmentation.input)
  segment.tags = Set({ tag })
  segmentation:add_segment(segment)
  return false
end

M.translator = {
  init = function(env)
    env.readings = ReverseLookup("terra_pinyin")
    env.codes = ReverseLookup("liur.extended")
    env.to_traditional = Opencc("s2t.json")
    env.memory = Memory(env.engine, env.engine.schema, "homophone_readings")
    env.source_translators = {}
    for _, name in ipairs({ "homophone", "homophone_simplified", "homophone_japanese" }) do
      env.source_translators[name] = Component.Translator(env.engine, env.engine.schema, name, "table_translator")
    end
  end,
  func = function(input, segment, env)
    local command = commands[input]
    if segment:has_tag("liur_command") then
      if command then
        yield(Candidate("liur_command", segment.start, segment._end,
          command[2], "〔空白鍵切換〕"))
      end
      return
    end
    if segment:has_tag("homophone") then
      local context, name = env.engine.context, "homophone"
      if context:get_option("liur_japanese") then name = "homophone_japanese"
      elseif context:get_option("liur_simplified") then name = "homophone_simplified" end
      local translation = env.source_translators[name]:query(input, segment)
      if translation then
        for candidate in translation:iter() do yield(candidate) end
      end
      return
    end
    if not segment:has_tag("homophone_result") then return end

    local source = input:sub(3)
    local readings = env.readings:lookup(source)
    if readings == "" then
      readings = env.readings:lookup(env.to_traditional:convert(source))
    end
    local seen, found = {}, false
    for reading in readings:gmatch("%S+") do
      if env.memory:dict_lookup(reading, false, 0) then
        for entry in env.memory:iter_dict() do
          local text = entry.text
          if utf8.len(text) == 1 and not seen[text] then
            seen[text], found = true, true
            local codes = env.codes:lookup(text):gsub("~", "")
            local comment = "〔" .. reading .. "〕"
            if codes ~= "" then comment = comment .. " " .. codes end
            local candidate = Candidate("homophone_result", segment.start, segment._end, text, comment)
            candidate.preedit = "【同音字：" .. source .. "】"
            yield(candidate)
          end
        end
      end
    end
    if not found then
      local candidate = Candidate("homophone_result", segment.start, segment._end,
        source, "〔查無讀音，保留原字〕")
      candidate.preedit = "【同音字：" .. source .. "】"
      yield(candidate)
    end
  end,
}

return M
