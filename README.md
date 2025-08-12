# AI截图分析

一个方便的AI截图分析工具，快速使用AI解释你在屏幕上看到的东西，或让他帮你解题。

exe网盘链接：[https://o-zwz-o.lanzouq.com/iQO8333cn78h](https://o-zwz-o.lanzouq.com/iQO8333cn78h)  密码：52pj

Github 项目地址：[https://github.com/00000O00000/ask-ai-screenshot

软件目前处于测试版，可能存在Bug，若有问题，欢迎前往 Github 提交 issue。

本软件使用 Trae + Claude 4 编写，然后由我和 Claude 4 共同进行用户体验优化。

## 功能特点

- **核心功能**：截图后，将图片OCR为文字或直接提交给AI，并自动显示AI回复结果
- **可扩展性**：使用提示词自定义功能，例如 一键截图做题、解释、翻译 等功能
- **高度自由**：可自行配置使用的AI接口、OCR接口、提示词

## 注意事项

- 只有多模态模型允许直接提交图片，目前常用的多模态模型为 Claude 3/4 系列，gpt-4o，QvQ-72B。现在常见的Qwen3全系列、Deepseek系列、Kimi-K2都不是多模态模型，需要先OCR后再提交。如果你发现模型报错400，请检查此配置是否正确。
- 需要联网功能，请使用秘塔API，有赠送额度，且付费很便宜。

## 技术架构
- 语言：Python
- GUI：PyQt6
- 截图：PIL
- 快捷键：pynput
- AI引擎：Requests

## 推荐AI服务商

| 名称     | 推荐理由                    | 链接地址                                   |
| -------- | --------------------------- | ------------------------------------------ |
| 硅基流动 | 模型齐全，稳定，价格合理    | https://cloud.siliconflow.cn/models        |
| 魔搭社区 | Qwen3全系列，每日2000次免费 | https://www.modelscope.cn/my/myaccesstoken |
| 秘塔AI   | 超强、超快联网搜索          | https://metaso.cn/search-api/playground    |
| V3 API   | 最全中转商，400+模型        | https://api.gpt.ge/register?aff=TVyz       |

## 腾讯OCR配置步骤

腾讯云OCR每月有1000次OCR调用次数，如果对精度有要求，推荐使用此OCR

1. **登录腾讯云**：前往链接，登录控制台。https://console.cloud.tencent.com

2. **开通OCR服务**：前往链接，开通OCR服务。https://console.cloud.tencent.com/ocr/overview

3. **获取密钥对**：前往链接，获取 `SecretID` 和 `SecretKey` ，保存到本地。https://console.cloud.tencent.com/cam/capi

4. **等待额度到账**：回到开通服务界面，持续刷新，等待免费的1000额度到账，然后在软件中配置密钥对，开始使用OCR服务。

## 许可证

本项目仅供学习和个人使用，不得用于任何商业化用途。

图标来源iconfont，[链接](https://www.iconfont.cn/collections/detail?spm=a313x.user_detail.i1.dc64b3430.6b413a81uspeMj&cid=17714)

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的截图、OCR和AI分析功能
- 完整的配置管理系统
- 多种通知方式
- 现代化的用户界面

## 计划添加的功能

- 多模型同时提问