#!/usr/bin/env python3
"""下載官方 CKIP 權重，匯出僅計算最後一個遮罩字的 ONNX 模型。

在隔離的建置環境安裝 torch>=2.6、transformers>=4.51,<5、onnx 後執行。
日常輸入只使用 numpy/onnxruntime，不需要 PyTorch 或 Transformers。
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REVISION = "d1edf497761caf4fdd83d2c4488132a8c56f9e3c"
SOURCE = "https://huggingface.co/ckiplab/albert-tiny-chinese"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    original = output / "original"
    original.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "pytorch_model.bin", "vocab.txt", "README.md"):
        target = original / name
        if not target.exists():
            subprocess.run(["curl", "-fL", "--retry", "2", "--max-time", "120",
                            f"{SOURCE}/resolve/{REVISION}/{name}", "-o", str(target)], check=True)

    import torch
    from transformers import AutoModelForMaskedLM

    class LastMaskedToken(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, input_ids, attention_mask, token_type_ids):
            hidden = self.model.albert(input_ids=input_ids, attention_mask=attention_mask,
                                       token_type_ids=token_type_ids).last_hidden_state
            return self.model.predictions(hidden[:, -2, :])

    torch.set_num_threads(1)
    model = AutoModelForMaskedLM.from_pretrained(original, local_files_only=True,
                                               attn_implementation="eager").eval()
    wrapped = LastMaskedToken(model).eval()
    ids = torch.tensor([[101, 509, 103, 102]], dtype=torch.int64)
    torch.onnx.export(wrapped, (ids, torch.ones_like(ids), torch.zeros_like(ids)),
                      str(output / "model.onnx"), input_names=["input_ids", "attention_mask", "token_type_ids"],
                      output_names=["logits"], opset_version=17, dynamo=False,
                      dynamic_axes={name: {0: "batch", 1: "sequence"}
                                    for name in ("input_ids", "attention_mask", "token_type_ids")})
    (output / "vocab.txt").write_bytes((original / "vocab.txt").read_bytes())
    manifest = {"source": SOURCE, "revision": REVISION, "license": "GPL-3.0",
                "export": "ALBERT masked language model, final masked position only",
                "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                           for name in ("model.onnx", "vocab.txt")}}
    (output / "provenance.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
