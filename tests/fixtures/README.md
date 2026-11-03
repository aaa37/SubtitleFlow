# 测试素材

speech-original.wav 为本项目原创英文句子经 espeak-ng 1.51 en-us 合成，非下载录音，未使用真人身份声音。用于验证功能，不代表对真实视频质量的评估。合成脚本：scripts/generate_media.py；本次在受限 Linux 环境中使用 Ubuntu 官方包临时解包的 espeak-ng，未将合成工具加入产品。

原句：Hello, welcome to Subtitle Flow. This is a local speech recognition test. We create subtitles on your computer.

此原创测试文字及其合成测试录音由本项目提供，可随项目用于测试、修改和再分发；它们不是需要分发 GPL 源码的 espeak-ng 程序本体。输出录音仅为开发测试资源，不是客户字幕处理所需依赖。

## 中文真人录音

fleurs-cmn-test-1906.wav 来自 Google FLEURS 数据集，配置 cmn_hans_cn、test split、样本 id 1906、原文件名 10026684690566417990.wav。作者/归属：Google FLEURS 项目及该数据集贡献者。依据官方数据集标注的 CC BY 4.0 使用，并在此署名。许可证：https://creativecommons.org/licenses/by/4.0/ 。数据集：https://huggingface.co/datasets/google/fleurs ；许可确认：https://huggingface.co/datasets/google/fleurs/discussions/2 。提取自官方 Parquet 转换的 test/0000.parquet，下载于 2026-11-02；原录音字节未经修改，测试时会由 FFmpeg 重采样并封装为测试视频。

参考句：“这并不是告别。这是一个篇章的结束，也是新篇章的开始。”

它用于一条中文功能回归，不能用于宣称总体识别准确率、所有口音的效果或人工录音都无误。
