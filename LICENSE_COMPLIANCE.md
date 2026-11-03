# 商业发行许可证审查记录

审查日期：2026-11-02。状态：**候选实现，尚未批准销售发行**。本文件记录工程措施和发行义务，不替代发行方对最终产物的合规审查。

## 已采取的工程措施

- whisper.cpp / FFmpeg 只从官方固定源码和固定 SHA-256 获取，自行构建。模型来自维护者转换仓库，固定修订与 SHA-256，不使用 `.en` 权重处理中文。
- FFmpeg 采用独立进程、LGPL 配置；不启用 `--enable-gpl`、`--enable-nonfree`、`--enable-version3`。`--disable-autodetect` 防止意外引入 GPL/非自由外部依赖。完整源码档与 configure 脚本随候选包保存。构建命令、源档哈希是可复查依据，不能仅看文件名认定 LGPL。
- Qt/PySide6 使用 onedir 动态加载；不使用 UPX、加密、DLL 校验锁或 DRM。明确排除 WebEngine、Charts 等未使用模块。最终包仍需审计实际插件和间接依赖。
- 允许用户为行使 LGPL 权利替换对应库并运行，允许为调试所修改 LGPL 库而进行的逆向工程。任何正式 EULA 不得限制这些权利。
- 构建脚本收集 installed wheel 原始许可与通知。FFmpeg/whisper.cpp 原始许可保存在 licenses/，完整源码含其嵌套第三方通知。

## 必须在销售前完成的 Qt / PySide 工作

1. 对最终 `_internal` 做 DLL 和 plugin 清单，确认只含 LGPL 可用模块及各自第三方许可。检查 CPython、OpenSSL、图像库、ICU 等实际被 PyInstaller 收入的二进制，而非凭 pip 名称猜测。
2. 为实际 Qt 6.8.3 库、PySide/Shiboken 6.8.3 准备完整对应源码及必要构建说明；上游源码入口为 https://download.qt.io/archive/qt/6.8/6.8.3/ 和 https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/ 。应在发行方长期维护的同一下载站提供实际对应源码，或履行符合许可要求的书面提供承诺；仅给上游链接不自动完成义务。
3. 补齐真实发行者名称、客服入口、对应源码下载 URL；验证所有许可副本可访问，并在商品页标注开源技术。
4. 用兼容的自建/修改 Qt/PySide 库替换 onedir 内库，实际验证程序能启动，提供目录和操作说明。PyInstaller 的库收集方式本身不是完成重新链接验证的证据。可以随产品提供应用层源码和构建脚本进一步简化替换。

## FFmpeg 特别注意

官方说明：https://ffmpeg.org/legal.html 。开启 GPL 选件会改变 FFmpeg 整体许可；nonfree 构建可能不可再分发。本项目不使用网上未审查的「full」静态包，也不将本开发环境的系统 FFmpeg 作为客户发行文件。不能把“用户首次自行下载二进制”作为规避许可证义务的办法。

当前脚本从源码构建限定配置，因此 GUI 的修复入口选择完整发行包的组件文件夹即可；不让用户临时安装编译工具。构建失败或源档/配置无法确认时，不应销售依赖缺失的工具包。

## 其他发行事项

- 保存 Python 完整 LICENSE（包括嵌套库通知）、PyInstaller 例外、所有实际运行时第三方声明。
- Microsoft 运行时须依据实际安装工具链的可再发行条款审核；数字签名证书、商标、销售平台规则另行处理。
- 明确本产品是自有 GUI/工作流封装，不冒用 OpenAI、Qt、FFmpeg 背书。
- 应用层商业许可、售后承诺、退款范围由发行方制定；不要删除第三方权利或作不存在的授权保护承诺。

## 发布闸门

`release-review.json` 所有字段目前为 false，客服及源码 URL 留空。`package_release.py --sale` 会拒绝不完整记录；默认只能制作候选包。自动化布尔闸门是提醒机制，不能判断法律合规。Windows CI 尚未运行，库清单、替换验证和 Windows 真机验收均待完成。

## 0.1.1 加固更新

新增 scripts/fetch_legal_sources.py，官方 Qt 镜像元数据固定哈希，发行脚本实际核验后携带三份对应源档和应用源码。实际 Windows 运行库清单、替换验证和发行审阅仍未完成。source_offer_url 不再是脚本的必填条件，因为采用直接附带源码；真实客服信息及未完成审阅字段仍是发行条件。
