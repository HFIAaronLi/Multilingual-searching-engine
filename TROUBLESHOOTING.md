[TROUBLESHOOTING.md](https://github.com/user-attachments/files/34212472/TROUBLESHOOTING.md)
# Troubleshooting / 故障排查

[Back to README / 返回 README](README.md) · [Safari setup / Safari 设置](README.md#2d-optional-google-safari-fallback--可选-google-safari-同会话回退) · [Windows Edge setup / Windows Edge 设置](README.md#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退)

Run `:errors` first for engine-specific diagnostics. For Safari permission problems, run `:browser check`; if it fails, run `:browser setup` and change the indicated setting yourself.

引擎问题请先运行 `:errors` 查看具体诊断。Safari 权限问题请运行 `:browser check`；若检测失败，再运行 `:browser setup`，并由你本人修改对应设置。

## Quick navigation / 快速导航

[Google](#google-returns-an-unreadable-page-or-verification--google-返回无法识别的页面或验证页) · [Safari](#safari-permission-error-or-no-safari-window--safari-权限错误或未打开窗口) · [Windows Edge](#edge-does-not-launch-on-windows--windows-上-edge-无法启动) · [Installation and launch / 安装与启动](#why-did-the-original-fail-in-macos-terminal--原版为什么在苹果终端中失败)

## Yahoo shows HTTP 500 or INKApi Error / Yahoo 显示 500 或 INKApi Error

HTTP 500 means the global endpoint returned an error rather than a result page, so a static result parser cannot turn that response into search results. The built-in `yahoo` retries the same `search.yahoo.com` request once and retains session cookies. It does not conceal the error by switching to Yahoo Japan. With `:browser on`, it can then try the same global URL in Chromium; if that also fails, `:errors` reports both failures.

HTTP 500 表示全球入口返回的是错误而非结果页，静态解析器无法把这种响应变成搜索结果。内置 `yahoo` 会重试同一个 `search.yahoo.com` 请求一次并保留会话 Cookie，不会通过切换到雅虎日本来掩盖错误。开启 `:browser on` 后，还可以用 Chromium 尝试同一个全球地址；如果仍然失败，`:errors` 会同时报告两次失败。

## Google returns an unreadable page or verification / Google 返回无法识别的页面或验证页

On macOS, enter `:browser safari` and complete the one-time permissions in [README section 2D](README.md#2d-optional-google-safari-fallback--可选-google-safari-同会话回退). On Windows, install the control package in [README section 2E](README.md#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退) and enter `:browser edge`; no Chromium download is needed. After the two static Google attempts fail, the selected browser opens the same original search URL with JavaScript support. If a CAPTCHA or consent page appears, complete it in the opened browser window. If the rendered page still cannot be parsed, `:errors` retains both the static error and a specific browser-rendered layout error; it does not misreport the page as an empty result set.

在 macOS 上，请输入 `:browser safari` 并完成 [README 2D 节](README.md#2d-optional-google-safari-fallback--可选-google-safari-同会话回退)的首次授权。在 Windows 上，请按 [README 2E 节](README.md#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退)安装控制包并输入 `:browser edge`，无需下载 Chromium。两个 Google 静态入口都失败后，所选浏览器会结合 JavaScript 支持打开同一个原搜索地址。若出现验证码或同意页，请在打开的浏览器窗口中完成。如果渲染后的页面仍无法解析，`:errors` 会同时保留静态错误和明确的浏览器渲染布局错误，不会把该页面误报为空结果。

## Baidu or DuckDuckGo returns a verification page / 百度或 DuckDuckGo 返回验证页

The built-in providers retry Baidu Mobile or DuckDuckGo HTML/Lite as applicable. Being in Japan does not itself create or remove a Baidu verification requirement; the website decides that for each connection and session. If all static endpoints return verification or consent pages, enable the optional `:browser on` fallback and complete the challenge yourself in Chromium. Without browser fallback, the program reports the verification page rather than treating it as an empty result set. `:browser safari` does not currently retry these two engines.

内置引擎会按情况重试百度移动版或 DuckDuckGo HTML／Lite。身在日本本身不会必然产生或解除百度的验证要求，网站会针对每次连接和会话自行判断。如果所有静态入口都返回验证或同意页，可开启可选的 `:browser on`，并在 Chromium 中亲自完成验证。未开启浏览器回退时，程序会如实报告验证页，而不是把它当成空结果。`:browser safari` 目前不会重试这两个引擎。

## Brave HTTP 429 / Brave 返回 429

This is rate limiting, not a result-layout problem. Wait before using Brave again. The program deliberately does not retry a 429 response through Chromium, because sending the same request through another client immediately can worsen the limiting.

这是访问频率限制，不是结果布局问题。请等待一段时间再使用 Brave。程序故意不通过 Chromium 重试 429，因为立即换客户端重复请求可能加重限流。

## Safari permission error or no Safari window / Safari 权限错误或未打开窗口

The earlier no-Safari retry in the real-Mac transcript was caused by stale same-query state: changing or re-selecting the browser mode did not invalidate the previous search. `:pool google` cleared it accidentally and allowed Safari to run. This is fixed in the current program; `:pool google` is no longer needed to force a refresh.

此前实机记录中“重新搜索却没有 Safari”的直接原因是同一查询保留了旧状态：切换或重新选择浏览器模式没有使前一次搜索失效，而 `:pool google` 恰好清除了它，使 Safari 得以执行。当前程序已经修复；不再需要靠 `:pool google` 强制刷新。

If Safari still does not open in the current version, follow this order:

如果当前版本仍没有打开 Safari，请按以下顺序排查：

1. Launch the intended updated `tsearch.py`. If Safari mode is saved, read the startup static-check message; it reports missing macOS/Safari/`osascript` prerequisites without launching Safari. 启动准备使用的最新版 `tsearch.py`。如果已保存 Safari 模式，先查看启动静态检查结果；它会在不打开 Safari 的情况下报告 macOS、Safari 或 `osascript` 前置条件是否缺失。
2. Enter `:browser check`. The program should open or reuse its dedicated `about:blank` tab and identify whether Automation, Apple-Events JavaScript, or DOM reading failed. 输入 `:browser check`。程序应打开或复用专用 `about:blank` 标签页，并指出自动化、Apple 事件 JavaScript 或 DOM 读取中的失败阶段。
3. If the check fails, enter `:browser setup`, personally change the indicated permission, and run `:browser check` again. If macOS asks for permission to control Safari, choose Allow. 若检测失败，输入 `:browser setup`，由你本人修改对应权限后再次检测。如果 macOS 弹出控制 Safari 的授权窗口，请选择“允许”。
4. After the check passes, repeat the same query. A previous Google failure is cleared automatically; re-selecting `:browser safari` also forces a fresh attempt. 检测通过后重复同一搜索词。此前的 Google 失败会自动清除；重新输入 `:browser safari` 也会强制重新尝试。
5. Look for **Safari fallback / Safari 回退: google** and check whether the dedicated Safari window opened behind other windows. 注意终端是否出现 **Safari fallback / Safari 回退: google**，并检查专用 Safari 窗口是否被其他窗口挡住。
6. Run `:errors`. If the Google entry contains only the two static errors and no Safari fallback diagnostic, the Safari attempt did not complete or was not reached in that process; this is not proof that Google had no results. 运行 `:errors`。如果 Google 条目仍只有两个静态错误且没有任何 Safari 回退诊断，说明该进程中的 Safari 尝试没有完成或根本没有执行到；这不能证明 Google 没有结果。
7. For a cleaner observation only, enter `:pool google` and repeat the search. Restore the desired pool afterwards. 如果只是想让过程更容易观察，可输入 `:pool google` 后重试，完成后恢复所需搜索池；这不是刷新缓存的必要手段。

Safari mode works only on macOS and currently retries Google only. If you close the dedicated window, run the search again; the program will create a new one.

Safari 模式仅支持 macOS，目前只重试 Google。如果关闭了专用窗口，重新搜索即可，程序会新建一个。

## Edge does not launch on Windows / Windows 上 Edge 无法启动

Confirm that Microsoft Edge is installed, then install Playwright with the exact command in [README section 2E](README.md#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退). Edge mode uses Playwright's `msedge` channel and does not need a Chromium installation. If launch still fails, use `:errors` for the detailed reason or switch to `:browser on` after completing [README section 2C](README.md#2c-optional-chromium-fallback--可选-chromium-浏览器回退).

请确认已安装 Microsoft Edge，再按 [README 2E 节](README.md#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退)的准确命令安装 Playwright。Edge 模式使用 Playwright 的 `msedge` 渠道，不需要安装 Chromium。如果仍无法启动，请用 `:errors` 查看详细原因，或完成 [README 2C 节](README.md#2c-optional-chromium-fallback--可选-chromium-浏览器回退)后改用 `:browser on`。

## Why did the original fail in macOS Terminal? / 原版为什么在苹果终端中失败？

The pasted original source passes a Python 3 syntax check, so a definite cause cannot be identified without the actual Terminal error. The most common causes are using `python` instead of `python3`, missing packages, running from the wrong directory, a `.txt` suffix, or accidentally saving Markdown fences with the code.

你贴出的原版代码可以通过 Python 3 语法检查，因此没有实际报错信息时，无法断定唯一原因。常见原因包括：误用 `python` 而不是 `python3`、缺少依赖、运行目录不正确、文件带有 `.txt` 后缀，或把 Markdown 代码标记一起保存了进去。

The installation commands in [README section 2A](README.md#2a-macos-installation-and-launch--macos-安装与运行) avoid these issues by using an explicit Python 3 environment and its full interpreter path.

[README 2A 节](README.md#2a-macos-installation-and-launch--macos-安装与运行)的安装命令通过明确的 Python 3 环境和完整解释器路径来避开这些问题。

## `No module named requests`, `bs4`, or `rich` / 提示缺少模块

Install dependencies with the same interpreter that launches the program. The commands in README sections [2A](README.md#2a-macos-installation-and-launch--macos-安装与运行) and [2B](README.md#2b-windows-installation-and-launch--windows-安装与运行) already do this.

请使用启动程序的同一个 Python 解释器安装依赖。README [2A](README.md#2a-macos-installation-and-launch--macos-安装与运行) 和 [2B](README.md#2b-windows-installation-and-launch--windows-安装与运行) 中的命令已经按此方式处理。

## `externally-managed-environment` on macOS / macOS 提示环境受系统管理

Use the virtual-environment commands in [README section 2A](README.md#2a-macos-installation-and-launch--macos-安装与运行) instead of installing packages into Homebrew or system Python.

请使用 [README 2A 节](README.md#2a-macos-installation-and-launch--macos-安装与运行)中的虚拟环境命令，不要直接向 Homebrew 或系统 Python 安装软件包。

## `can't open file` or `No such file or directory` / 找不到文件

Check that Terminal is in the folder containing `tsearch.py`:

请确认终端当前目录中存在 `tsearch.py`：

- macOS: run `ls` / macOS：执行 `ls`。
- Windows: run `dir` / Windows：执行 `dir`。

Then use `cd` to enter the actual folder where the file is saved.

如果文件不在当前目录，请用 `cd` 进入实际保存位置。

## `Permission denied` on macOS / macOS 提示权限不足

Do not run `./tsearch.py`. Launch it through Python as shown:

不要直接执行 `./tsearch.py`，请按以下方式通过 Python 启动：

```bash
.tsearch-venv/bin/python tsearch.py
```

## A `SyntaxError` appears / 出现语法错误

Use the supplied `tsearch.py` directly, make sure the file contains Python code only, and launch it with Python 3 rather than Python 2.

请直接使用提供的 `tsearch.py`，确保文件中只有 Python 代码，并使用 Python 3 而不是 Python 2 启动。
