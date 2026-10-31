# Multilingual-searching-engine-with-no-ads-with-better-answers-and-location-adjustment-supporting[README-3.md](https://github.com/user-attachments/files/34212417/README-3.md)
# Terminal Search / 终端搜索

A bilingual terminal search tool with unrestricted-language search by default, ad filtering, result previews, and on-demand paragraph summaries.

一个默认不限搜索语言的中英双语终端搜索工具，支持广告过滤、结果预览，以及按需提取网页段落摘要。

## Quick navigation / 快速导航

**New users only need these five steps; the remaining sections are references. / 新用户只需按以下五步走，其余章节均可按需查阅。**

1. [Save `tsearch.py` / 保存程序](#1-save-the-program--保存程序)。
2. Install and launch on [macOS](#2a-macos-installation-and-launch--macos-安装与运行) or [Windows / Windows 安装](#2b-windows-installation-and-launch--windows-安装与运行)。
3. [Enter a normal query / 输入搜索词](#3-basic-use--基本使用)。
4. Optionally configure a Google browser fallback: [Safari on macOS](#2d-optional-google-safari-fallback--可选-google-safari-同会话回退), [installed Edge on Windows](#2e-optional-google-edge-fallback-for-windows--windows-可选-google-edge-回退), or [separate Chromium](#2c-optional-chromium-fallback--可选-chromium-浏览器回退)。按需配置 Google 浏览器回退。
5. If something fails, open [Troubleshooting / 故障排查](TROUBLESHOOTING.md)。

**Reference / 参考章节：** [Requirements / 环境要求](#requirements--环境要求) · [Improvements / 改进内容](#improvements--改进内容) · [Commands / 命令](#4-commands--命令) · [Search engines / 搜索引擎](#5-search-engines--搜索引擎)。

## Improvements / 改进内容

- **Unrestricted language by default / 默认不限语言：** `auto` no longer guesses Chinese or English and does not add a language or region condition to the query. `auto` 不再把查询自动归为中英文，也不会给查询附加语言或地区条件。
- **Optional language setting / 可主动设置语言：** use commands such as `:lang zh`, `:lang en`, `:lang ja`, or `:lang fr`. 可使用 `:lang zh`、`:lang en`、`:lang ja`、`:lang fr` 等命令主动指定搜索语言。
- **Ad and junk filtering / 广告及垃圾内容过滤：** enabled by default; known advertising hosts and explicit ad labels are removed. 默认开启，会过滤已知广告域名和明确的广告标识。
- **Paragraph previews / 段落预览：** results show the beginnings of P1, P2, and Last when those text units are available. 结果会尽量分别显示首段、次段和末段的开头。
- **On-demand page summaries / 按需网页摘要：** `:summary <number>` fetches a selected page and extracts its first, second, and last paragraphs. `:summary <编号>` 会读取指定网页并提取首段、次段和末段。
- **Always bilingual / 始终双语：** the interface displays English first, followed by Chinese; there is no interface-language selection step. 界面固定为英文在前、中文在后，不需要选择界面语言。
- **More built-in engines / 更多内置引擎：** Google, Bing, DuckDuckGo, Yahoo, Yahoo Japan, Baidu, Brave, Ecosia, Yandex, Mojeek, and Sogou are available. 内置 Google、Bing、DuckDuckGo、Yahoo、雅虎日本、百度、Brave、Ecosia、Yandex、Mojeek 和搜狗。
- **Yahoo Global stays global / 全球 Yahoo 不再换站：** the built-in `yahoo` uses only `search.yahoo.com`. It keeps session cookies and retries that same global endpoint once after a 5xx response; it never substitutes Yahoo Japan. `yahoojp` remains a separate, explicitly selected engine. 内置 `yahoo` 只访问 `search.yahoo.com`，保留会话 Cookie，并在收到 5xx 后重试同一个全球入口一次，绝不会擅自改用雅虎日本；`yahoojp` 仍是需要明确选择的独立引擎。
- **Compatible static-page parsing / 静态网页解析兼容：** Google has a basic-HTML retry, DuckDuckGo supports HTML GET/POST and Lite, and Baidu can retry its mobile result page. Google 增加基本 HTML 重试；DuckDuckGo 支持 HTML GET／POST 和 Lite；百度可自动重试移动版结果页。
- **Specific page diagnostics / 明确的页面诊断：** `:errors` distinguishes CAPTCHA/security checks, consent pages, explicit no-results pages, unrecognized layouts, HTTP errors, and connection failures, and includes the page title and final URL when available. `:errors` 会区分验证码／安全检查、同意页、明确无结果、布局无法识别、HTTP 错误和连接失败，并尽量显示网页标题与最终地址。
- **Optional real-browser fallback / 可选真实浏览器回退：** `:browser on` retries failed static engines in Chromium using the original search URL, executes JavaScript, and keeps a separate persistent browser profile. It never changes Yahoo Global to Yahoo Japan, does not repeat HTTP 429 requests, and never solves CAPTCHA automatically. 开启 `:browser on` 后，失败的静态引擎会在 Chromium 中按原搜索地址重试、执行 JavaScript，并使用独立的持久浏览器配置。不会把全球 Yahoo 换成雅虎日本，不会对 HTTP 429 重复请求，也不会自动破解验证码。
- **Google Safari-session fallback / Google Safari 同会话回退：** on macOS, `:browser safari` uses Safari itself after static Google fails. It opens the original Google search URL in a dedicated Safari window/tab and reads the rendered DOM; no Playwright or Chromium download is needed. This scoped mode currently handles Google only. macOS 上可输入 `:browser safari`，让静态失败后的 Google 改用 Safari 本身：在专用 Safari 窗口的标签页中打开原 Google 搜索地址并读取渲染后的 DOM，不需要下载 Playwright 或 Chromium。该模式目前只处理 Google。
- **Google installed-Edge fallback for Windows / Windows 使用已安装 Edge 的 Google 回退：** `:browser edge` launches the installed Microsoft Edge with a dedicated persistent profile after static Google fails. It needs the Playwright control package but no Chromium browser download. Results are marked `edge:google`. Windows 上可输入 `:browser edge`，在静态 Google 失败后调用已安装的 Microsoft Edge，并使用独立的持久配置。只需安装 Playwright 控制包，不需要下载 Chromium；结果来源显示 `edge:google`。
- **Custom engine domains / 自定义域名引擎：** enter a domain such as `yahoo.hk`, `yahoo.co.jp`, or `baidu.com` directly in `:pool`; no provider editing is needed. 可在 `:pool` 中直接输入 `yahoo.hk`、`yahoo.co.jp`、`baidu.com` 等域名，无需修改程序。
- **Real next-page fetching / 真正的下一页：** when cached results run out, the program requests the next result page from the selected engines and removes repeated URLs. 缓存结果用完后，程序会向所选引擎请求下一页，并移除重复网址。
- **Transparent relevance and counts / 透明的相关性与数量统计：** every result shows its score; `:score`, `:stats`, and `:errors` explain ranking, result counts, and engine failures. 每条结果都会显示分数；`:score`、`:stats` 和 `:errors` 分别解释排序、结果数量和引擎失败原因。
- **More reliable operation / 运行更稳妥：** adds HTTP error checks, safer result numbers, page-bound checks, and clearer error messages. 增加网络错误检查、编号与翻页边界检查，以及更清楚的提示。

## Requirements / 环境要求

- Python 3.9 or newer / Python 3.9 或更新版本。
- macOS or Windows / macOS 或 Windows。
- An internet connection / 可用的网络连接。

No separate compilation step is required. Run the file with Python 3.

不需要单独编译，直接使用 Python 3 运行即可。

## 1. Save the program / 保存程序

Save the supplied file as **`tsearch.py`** on your Desktop. Keep it as a UTF-8 Python file.

将提供的文件以 **`tsearch.py`** 为名保存到桌面，并保持 UTF-8 编码。

Do not rename it to `tsearch.py.txt`, and do not paste Markdown fences such as ```` ```python ```` into the file.

不要把它保存成 `tsearch.py.txt`，也不要把 ```` ```python ```` 等 Markdown 标记复制进文件。

## 2A. macOS installation and launch / macOS 安装与运行

Open **Terminal**. The following commands use a virtual environment, so they do not modify the system Python and do not require activating the environment.

打开“终端”。以下命令使用独立的虚拟环境，不修改系统 Python，也不需要执行环境激活命令。

### Check Python 3 / 检查 Python 3

```bash
python3 --version
```

If Terminal says `python3: command not found`, install Python 3 from <https://www.python.org/downloads/macos/>, then close and reopen Terminal.

如果提示 `python3: command not found`，请先从上述 Python 官网安装 Python 3，然后关闭并重新打开终端。

### Go to Desktop / 进入桌面目录

```bash
cd ~/Desktop
```

### Create an isolated environment / 创建独立环境

```bash
python3 -m venv .tsearch-venv
```

### Install dependencies / 安装依赖

```bash
.tsearch-venv/bin/python -m pip install requests beautifulsoup4 rich
```

PyYAML is no longer required.

新版不再需要 PyYAML。

### Launch / 启动

```bash
.tsearch-venv/bin/python tsearch.py
```

For later runs, only these two commands are needed:

以后再次运行时，只需执行：

```bash
cd ~/Desktop
.tsearch-venv/bin/python tsearch.py
```

## 2B. Windows installation and launch / Windows 安装与运行

Open **Windows Terminal** or **PowerShell**. These commands also use an isolated environment and do not require changing PowerShell's execution policy.

打开“Windows 终端”或 PowerShell。以下命令同样使用独立环境，不需要修改 PowerShell 执行策略。

### Check Python / 检查 Python

```powershell
py --version
```

If `py` is unavailable, try `python --version`; in the next command, replace `py` with `python`.

如果 `py` 不可用，请尝试 `python --version`，并在下一条创建环境的命令中用 `python` 替代 `py`。

### Go to Desktop / 进入桌面目录

```powershell
cd "$env:USERPROFILE\Desktop"
```

### Create an isolated environment / 创建独立环境

```powershell
py -m venv .tsearch-venv
```

### Install dependencies / 安装依赖

```powershell
.tsearch-venv\Scripts\python.exe -m pip install requests beautifulsoup4 rich
```

### Launch / 启动

```powershell
.tsearch-venv\Scripts\python.exe tsearch.py
```

For later runs, only these two commands are needed:

以后再次运行时，只需执行：

```powershell
cd "$env:USERPROFILE\Desktop"
.tsearch-venv\Scripts\python.exe tsearch.py
```

## 2C. Optional Chromium fallback / 可选 Chromium 浏览器回退

**The basic installation does not need Playwright or Chromium. Install this section only for `:browser on`. For Google with existing Safari on macOS, use section 2D instead; for Google with installed Edge on Windows and no Chromium download, use section 2E instead.**

**基本安装不需要 Playwright 或 Chromium。本节仅用于 `:browser on`。如果要在 macOS 上使用现有 Safari 处理 Google，请直接看 2D；如果要在 Windows 上使用已安装 Edge 处理 Google 且避免下载 Chromium，请直接看 2E。**

macOS:

```bash
.tsearch-venv/bin/python -m pip install playwright
.tsearch-venv/bin/python -m playwright install chromium
```

Windows PowerShell:

```powershell
.tsearch-venv\Scripts\python.exe -m pip install playwright
.tsearch-venv\Scripts\python.exe -m playwright install chromium
```

Then start the program normally and enable the feature once:

随后正常启动程序，并开启一次功能即可：

```text
:browser on
```

The setting is saved. Use `:browser off` to disable it. Chromium opens only after a static engine failure, not for engines that already returned results.

该设置会自动保存，输入 `:browser off` 可关闭。Chromium 只会在静态引擎失败后打开，不会重复抓取已经成功返回结果的引擎。

## 2D. Optional Google Safari fallback / 可选 Google Safari 同会话回退

**This mode is for macOS and currently handles Google only. It does not require Playwright, Chromium, or any additional Python package.**

**此模式仅用于 macOS，目前只处理 Google。不需要 Playwright、Chromium 或任何额外的 Python 包。**

### Optional first-run Google preparation / 可选的首次 Google 准备

If you already use Google in Safari, you can first open [google.com](https://www.google.com) in Safari yourself, sign in if you want to, and complete any consent page that appears. This optional preparation can make the first fallback less surprising because the dedicated window uses Safari's existing session. **A Google login is not required, and neither login nor a one-time consent guarantees that no consent page or CAPTCHA will appear later.** If one appears, complete it yourself in the dedicated Safari window; never send your account credentials to the terminal program.

如果你平时就在 Safari 中使用 Google，可以先由你本人在 Safari 里打开 [google.com](https://www.google.com)，按需登录账号，并完成当时出现的同意页面。这个可选准备能让首次回退更顺利，因为专用窗口会使用 Safari 的现有会话。**Google 登录不是必需步骤；无论是否登录或完成过一次同意，都不能保证以后不再出现同意页或验证码。**如果之后出现这些页面，请你在专用 Safari 窗口中亲自完成；不要向终端程序提供账号凭据。

Start the program normally, then enter:

正常启动程序，然后输入：

```text
:browser safari
```

Entering this command saves the mode and immediately runs a real permission check in one dedicated `about:blank` page. It does not open Google for that check. If the check fails, enter `:browser setup`, change the indicated permissions yourself, and then enter `:browser check` again.

输入此命令会保存模式，并立即在一个专用 `about:blank` 页面中执行真实权限检测；检测不会打开 Google。若检测失败，请输入 `:browser setup`，由你本人修改对应权限，然后再次输入 `:browser check`。

To test Google without other engines, you can optionally select it first:

如果你希望先单独测试 Google，也可先输入：

```text
:pool google
```

Then type a normal search query. The program first tries the existing static Google endpoints. Only if both fail does it ask Safari to open the original Google search URL. Results returned through this route have Source value `safari:google`.

随后正常输入搜索词。程序仍会先尝试现有 Google 静态入口；只有它们都失败时，才会让 Safari 打开原 Google 搜索地址。通过此途径取得的结果，来源栏显示 `safari:google`。

### Real-Mac verification result / Mac 实机验证结果

A real macOS run has completed this full route: after static Google failed, Safari opened the original Google search page, the page rendered normally, and the terminal read **7 Google results** marked `safari:google`. It verifies the Safari route on that Mac; it does not guarantee the same Google response on every Mac, network, or Google session.

已经在真实 macOS 上完整跑通一次：静态 Google 失败后，Safari 打开了原 Google 搜索页，页面正常渲染，终端最终读取到 **7 条来源为 `safari:google` 的 Google 结果**。它证明该 Safari 链路在这台 Mac 上可用，但不保证每台 Mac、每种网络或每个 Google 会话都会收到相同页面。

The full transcript also exposed a separate repeat-search cache bug. Previously, entering `:browser safari` and then repeating the same query could reuse the preceding static failure without calling Safari. Entering `:pool google` happened to clear that state, which allowed the successful run. The current program now invalidates the current search whenever a browser mode is entered, even when the same mode is selected again. A successful `:browser check` also clears a previous Google failure for the current query. The Safari route was verified on a real Mac; the later cache fix and the new startup/check/setup additions are covered by regression tests, but those later additions were not part of that earlier Mac transcript and should still be checked in the normal Mac workflow.

完整记录还暴露了一个独立的重复搜索缓存问题。此前输入 `:browser safari` 后再次搜索同一个词，可能直接复用前一次静态失败状态而不调用 Safari；输入 `:pool google` 恰好清除了该状态，所以随后成功。当前程序已改为：每次输入浏览器模式都会使当前搜索失效，即使重复选择同一个模式也一样；`:browser check` 成功后也会清除当前查询此前的 Google 失败。Safari 链路已在真实 Mac 上验证；后续的缓存修复以及新增的启动检查、`:browser check`、`:browser setup` 均已通过回归测试，但这些后加功能不在那次较早的 Mac 实机记录中，仍应在目标 Mac 的正常使用流程中复核。

### New-Mac minimum checklist / 新 Mac 最小配置清单

1. Install only the basic dependencies from section 2A; Safari mode needs neither Playwright nor Chromium. 只需按 2A 节安装基础依赖；Safari 模式不需要 Playwright 或 Chromium。
2. Start the program and enter `:browser setup`. It opens macOS Automation settings and Safari, and prints the exact manual steps. 启动程序并输入 `:browser setup`。它会打开 macOS 自动化设置和 Safari，并显示准确的手动步骤。
3. Personally enable terminal Automation access to Safari and Safari's JavaScript from Apple Events. The program cannot toggle these sensitive settings or enter your password. 由你本人允许终端控制 Safari，并开启 Safari 的“允许来自 Apple 事件的 JavaScript”。程序不能替你切换这些敏感设置，也不会输入你的密码。
4. Enter `:browser safari`. This enables the mode and runs the real blank-page check. If the mode was already enabled, enter `:browser check` instead. 输入 `:browser safari`，启用模式并执行真实空白页检测；如果此前已经启用该模式，则输入 `:browser check`。
5. After the check passes, run a normal query. For a clean first Google test, optionally enter `:pool google` and check for Source `safari:google` after the static attempts fail. 检测通过后正常搜索。首次清晰测试 Google 时，可选输入 `:pool google`，并在静态尝试失败后检查来源是否为 `safari:google`。
6. Restore any desired engine pool after the test; using Google alone is only a diagnostic step. 测试后可恢复所需搜索池；单独使用 Google 只是诊断步骤。

Safari's **Allow Remote Automation** option is not required by this implementation, because the program uses Apple Events rather than SafariDriver. A Google account login is also not mandatory. If Google shows consent or CAPTCHA, the user must complete it in Safari.

本实现不使用 SafariDriver，因此不需要开启 Safari 的“允许远程自动化”。也不强制登录 Google 账号；如果 Google 显示同意页或验证码，用户需要在 Safari 中亲自完成。

Proxy configuration is described under [Network availability](#network-availability--网络可用性) below.

代理配置请见下文的[网络可用性](#network-availability--网络可用性)一节。

### Startup, permission check, and setup commands / 启动、权限检测与设置命令

- **Startup static check / 启动静态检查：** if Safari mode was saved, each launch checks that the platform is macOS and that Safari.app and `osascript` exist in their standard locations. It does not launch Safari, send Apple Events, or claim that permissions are working. 如果上次保存的是 Safari 模式，每次启动会检查当前平台是否为 macOS，以及标准位置是否存在 Safari.app 和 `osascript`。启动检查不会打开 Safari、发送 Apple 事件，也不会把“文件存在”误报成“权限已通过”。
- **`:browser check` / 真实权限检测：** creates or reuses only the program's dedicated tab, navigates it to `about:blank`, then separately exercises Safari Automation, JavaScript from Apple Events, and DOM reading. It reads no Google page, cookies, history, passwords, or existing tabs. 它只会创建或复用程序的专用标签页，将其转到 `about:blank`，分别验证 Safari 自动化、来自 Apple 事件的 JavaScript 和 DOM 读取；不会读取 Google 页面、Cookie、历史记录、密码或现有标签页。
- **`:browser setup` / 设置引导：** opens **System Settings → Privacy & Security → Automation** and Safari, then displays the manual setup steps. It works without changing the saved browser mode and never enables a sensitive option for you. 它会打开“系统设置 → 隐私与安全性 → 自动化”和 Safari，并显示手动步骤；不会修改已保存的浏览器模式，也不会替你开启敏感选项。
- **Retry after repair / 修复后的重试：** when a real check succeeds after the current query previously failed at Google, that old failure state is cleared. Enter the same query again to retry; `:pool google` is not needed for cache clearing. 如果当前查询此前在 Google 失败，真实检测成功后会清除该旧失败状态。再次输入同一搜索词即可重试，不需要靠 `:pool google` 清除缓存。

Selecting `:browser safari` also runs the real check immediately. Startup itself remains static-only, so merely launching the program does not unexpectedly open Safari.

输入 `:browser safari` 时也会立即执行真实检测；程序启动本身仍只做静态检查，因此不会仅因启动程序就意外打开 Safari。

### One-time macOS and Safari permission setup / 首次授权

1. **Allow your terminal to control Safari / 允许终端控制 Safari。** On first use, macOS may display an automation prompt; choose Allow. If you previously denied it, open **System Settings → Privacy & Security → Automation**, find Terminal or iTerm, and enable Safari. 首次使用时，macOS 可能弹出自动化授权窗口，请选择“允许”。如果此前拒绝过，请打开“系统设置 → 隐私与安全性 → 自动化”，找到“终端”或 iTerm，并允许其控制 Safari。
2. **Show the Develop menu / 显示“开发”菜单。** Choose **Safari → Settings → Advanced → Show features for web developers**. 选择“Safari → 设置 → 高级 → 显示网页开发者功能”。
3. **Allow JavaScript from Apple Events / 允许来自 Apple 事件的 JavaScript。** Choose **Develop → Allow JavaScript from Apple Events**. On newer macOS versions, this may be inside **Develop → Developer Settings…**. 选择“开发 → 允许来自 Apple 事件的 JavaScript”；在较新的 macOS 中，该选项可能位于“开发 → 开发者设置…”里面。
4. If macOS requests a password to change this sensitive Safari setting, the Mac user must enter it personally. The program neither needs nor receives that password. 如果 macOS 在修改这个敏感 Safari 设置时要求输入密码，必须由 Mac 用户本人输入；程序不需要也不会取得该密码。
5. Return to the program and run `:browser check`. After it passes, repeat the same query; a previous Google failure is cleared automatically. Re-selecting `:browser safari` also forces a fresh attempt. 修改权限后返回程序并运行 `:browser check`。检测通过后重复同一搜索词即可，此前的 Google 失败会自动清除；重新输入 `:browser safari` 也会强制重新尝试。

### What this mode does and does not do / 功能边界

- Safari creates a dedicated window containing a dedicated tab. Existing tabs are not read or modified. Safari 会新建一个专用窗口，其中包含专用标签页；程序不会读取或修改现有标签页。
- Safari performs the web request, follows the website's own redirects, executes page JavaScript, and uses its existing normal browser session. The program reads only the dedicated tab's final URL and rendered HTML. 网页请求、网站自身跳转和 JavaScript 执行均由 Safari 完成，并使用 Safari 现有的普通浏览会话；程序只读取专用标签页的最终网址与渲染后 HTML。
- The program does not read or export Safari cookies, history, passwords, or other tabs. 程序不会读取或导出 Safari Cookie、历史记录、密码或其他标签页。
- If Google presents CAPTCHA or consent, complete it yourself in the dedicated Safari window. The program waits up to 90 seconds and never solves CAPTCHA automatically. 如果 Google 显示验证码或同意页，请你在专用 Safari 窗口中亲自完成；程序最多等待 90 秒，不会自动破解验证码。
- The setting is saved. Use `:browser off` for static-only operation or `:browser on` to switch back to independent Chromium. 该设置会保存；输入 `:browser off` 可恢复仅静态请求，输入 `:browser on` 可切回独立 Chromium。
- Yahoo, Brave, DuckDuckGo, and other engines are not retried through Safari in this version. 此版本不会通过 Safari 重试 Yahoo、Brave、DuckDuckGo 或其他引擎。

If you use multiple Safari profiles, make sure the dedicated window belongs to the same profile in which Google already works; otherwise its session cookies can differ.

如果你使用多个 Safari 用户场景／描述文件，请确认专用窗口属于已经能正常使用 Google 的同一个用户场景，否则其会话 Cookie 可能不同。

## 2E. Optional Google Edge fallback for Windows / Windows 可选 Google Edge 回退

**This mode uses the Microsoft Edge already installed on Windows. It does not download Chromium and does not read your everyday Edge profile. It currently handles Google only.**

**此模式会调用 Windows 中已经安装的 Microsoft Edge，不下载 Chromium，也不读取你的日常 Edge 配置。目前只处理 Google。**

From the Desktop folder in Windows PowerShell, install only the browser-control package with the same Python that runs the program:

在 Windows PowerShell 的桌面目录中，使用运行本程序的同一个 Python 安装浏览器控制包即可：

```powershell
.tsearch-venv\Scripts\python.exe -m pip install playwright
```

**Do not run `python -m playwright install chromium` for this mode.** Then start the program normally:

**此模式不需要执行 `python -m playwright install chromium`。**随后正常启动程序：

```powershell
.tsearch-venv\Scripts\python.exe tsearch.py
```

Enable the Windows Edge mode:

启用 Windows Edge 模式：

```text
:browser edge
```

To test Google alone, optionally select it first:

如果希望先单独测试 Google，也可先输入：

```text
:pool google
```

Then enter a normal search query. The two static Google endpoints are tried first. Only if both fail does the program launch installed Edge, open the original Google search URL, execute page JavaScript, and parse the rendered DOM. Results have Source value `edge:google`.

随后正常输入搜索词。程序仍会先尝试两个 Google 静态入口；只有它们都失败时，才会启动已安装的 Edge，打开原 Google 搜索地址、执行页面 JavaScript 并解析渲染后的 DOM。结果来源显示 `edge:google`。

### Edge profile and session boundary / Edge 配置与会话边界

- Edge mode uses the dedicated persistent profile `.tsearch-edge-profile` in your home directory. It keeps cookies between runs in that profile. Edge 模式使用主目录下的独立持久配置 `.tsearch-edge-profile`，会在该配置内保留多次运行之间的 Cookie。
- It does **not** attach to, copy, or read your everyday Edge profile. Therefore it is not the same existing Edge session; logins and cookies already present in your daily profile are not automatically available. 它**不会**连接、复制或读取你的日常 Edge 配置，因此不是现有 Edge 同会话；日常配置中的登录状态和 Cookie 不会自动出现。
- The first browser run may require Google consent or CAPTCHA again. Complete it yourself in the opened Edge window; the program waits up to 90 seconds and never solves CAPTCHA automatically. 首次浏览器运行可能需要重新完成 Google 同意确认或验证码。请在打开的 Edge 窗口中亲自完成；程序最多等待 90 秒，不会自动破解验证码。
- Yahoo, Brave, DuckDuckGo, and other engines are not retried through Edge in this mode. 此模式不会通过 Edge 重试 Yahoo、Brave、DuckDuckGo 或其他引擎。
- The setting is saved. Use `:browser off` for static-only operation or `:browser on` for the separate Chromium mode. 设置会保存；输入 `:browser off` 可恢复仅静态请求，输入 `:browser on` 可改用独立 Chromium 模式。
- If Edge is not installed or cannot launch, install Microsoft Edge or use `:browser on` with section 2C. `:errors` reports the actual launch problem. 如果未安装 Edge 或无法启动，请安装 Microsoft Edge，或按 2C 节改用 `:browser on`。`:errors` 会报告实际启动错误。

## 3. Basic use / 基本使用

When you see the following prompt, enter a query in any language:

看到以下提示后，可以用任意语言输入搜索内容：

```text
Search 搜索 >
```

Examples / 示例：

```text
Python decorators
巴黎 旅游
東京 ラーメン
inteligencia artificial
```

Enter only the topic you want to search. Do not paste the program's yellow engine-failure warning back into the search prompt as a query. Commands such as `:errors` are entered on their own line.

只需输入真正想搜索的主题，不要把程序黄色的引擎失败警告再粘贴为搜索内容。`:errors` 等命令应单独输入一行。

Type `:help` to see all commands, and `:exit` or `q` after a colon (`:q`) to quit.

输入 `:help` 查看全部命令；输入 `:exit` 或 `:q` 退出。

## 4. Commands / 命令

| Command / 命令 | Function / 功能 |
| --- | --- |
| `:new` | Start a new topic / 开始新话题 |
| `:next` or `n` / `:next` 或 `n` | Show cached results or fetch the next engine page / 展示缓存或抓取引擎下一页 |
| `:prev` or `p` / `:prev` 或 `p` | Previous page / 上一页 |
| `:open 1` | Open result 1 in the browser / 在浏览器中打开第 1 条结果 |
| `:summary 1` | Extract a paragraph summary from result 1 / 提取第 1 条结果网页的段落摘要 |
| `:score 1` | Show the relevance formula and matching tokens for result 1 / 查看第 1 条结果的相关性计算式和命中词元 |
| `:stats` | Show received, filtered, duplicate, and retained result counts / 查看抓取、过滤、重复和保留数量 |
| `:errors` | Show detailed engine connection or parsing errors / 查看引擎连接或解析错误详情 |
| `:pool` | Show available engines and the current pool / 查看可用引擎和当前搜索池 |
| `:pool bing,baidu` | Use Bing and Baidu / 使用 Bing 和百度 |
| `:pool google,yahoo.co.jp,baidu.com` | Mix built-in engines and custom domains / 混合使用内置引擎与自定义域名 |
| `:pool reset` | Restore the expanded default pool / 恢复扩展后的默认搜索池 |
| `:lang auto` | Remove the explicit language setting / 取消主动语言设置 |
| `:lang ja` | Request Japanese results / 请求日文搜索结果 |
| `:lang zh-CN` | Request Simplified Chinese results / 请求简体中文搜索结果 |
| `:filter on` | Enable ad and junk filtering / 开启广告及垃圾内容过滤 |
| `:filter off` | Disable filtering / 关闭过滤 |
| `:browser on` | Enable Chromium fallback after static engine failures / 静态引擎失败后启用 Chromium 回退 |
| `:browser safari` | Enable Google-only Safari fallback and run its blank-page permission check / 启用仅 Google 的 Safari 回退并执行空白页权限检测 |
| `:browser edge` | Enable Google-only installed-Edge fallback on Windows / 在 Windows 上启用仅 Google 的已安装 Edge 回退 |
| `:browser check` | Test Safari Automation, Apple-Events JavaScript, and DOM reading with `about:blank` / 用 `about:blank` 检测 Safari 自动化、Apple 事件 JavaScript 和 DOM 读取 |
| `:browser setup` | Open macOS Automation settings and Safari with manual instructions / 打开 macOS 自动化设置和 Safari 并显示手动步骤 |
| `:browser off` | Disable browser fallback / 关闭浏览器回退 |
| `:exit` or `:q` | Quit / 退出 |

The search language, pool, custom engines, filtering setting, and browser-fallback setting are saved in `.tsearch.json` in your home directory.

搜索语言、搜索池、自定义引擎、过滤设置和浏览器回退设置会保存在用户主目录下的 `.tsearch.json` 中。

### Language behavior / 语言行为说明

`auto` means no additional language restriction. Other language codes are passed to engines that support language or regional preferences. Search engines can still occasionally return pages in other languages; Baidu does not provide a general language-control parameter in this tool.

`auto` 表示不附加语言限制。其他语言代码会传递给支持语言或地区设置的引擎。搜索引擎仍可能偶尔返回其他语言的网页；本工具中的百度搜索没有通用的语言控制参数。

This setting never changes the bilingual interface.

该设置不会改变中英双语界面。

### Filtering and summaries / 过滤与摘要说明

Filtering is enabled by default. If you are researching advertising itself and believe a useful result was removed, use `:filter off`.

广告过滤默认开启。如果你正在研究广告相关内容，并认为有用结果被误过滤，可使用 `:filter off`。

The search table builds its short preview from search-result text. Use `:summary <number>` to read the selected public page and show the beginnings of its first, second, and last available paragraphs. Sites that require login, block automated access, use only JavaScript-rendered text, or return non-HTML content may not be summarizable.

结果表格中的简短预览来自搜索结果文本。使用 `:summary <编号>` 可读取对应的公开网页，并显示首段、次段和末段的开头。需要登录、阻止自动访问、仅通过 JavaScript 生成正文，或返回非 HTML 内容的网站可能无法生成摘要。

### Real pagination and result counts / 真正的分页与结果数量

The first search reads the first result page from each selected engine. Each provider contributes up to 10 parsed results per fetch. The program then removes invalid entries, explicit ads or junk when filtering is enabled, and duplicate URLs. It does **not** remove results for having a low relevance score.

首次搜索会读取每个所选引擎的第一页。每个引擎每次最多提供 10 条可解析结果，随后程序会移除无效条目、过滤开启时的明确广告或垃圾内容，以及重复网址。**不会因为相关性分数低而删除结果。**

If more than 10 results are already loaded, `:next` first moves through that local cache. When the cache is exhausted, `:next` requests the next page from the engines. New URLs are appended; repeated URLs are not presented as a new page. If a fetch produces no new URLs, the program reports that there are no more new results.

如果已经加载超过 10 条结果，`:next` 会先浏览本地缓存。缓存用完后，`:next` 会向引擎请求下一页，并追加新网址；重复网址不会被伪装成新的一页。如果一次抓取没有产生新网址，程序会明确提示没有更多新结果。

Use `:stats` to see exactly why a batch has a particular size. For example, 10 received results minus 1 duplicate means 9 retained results. If an engine only returned 9 readable results, the statistics will show 9 received instead.

使用 `:stats` 可以准确查看某批结果数量的来源。例如，引擎返回 10 条、重复 1 条，最终就是 9 条。如果引擎本身只返回 9 条可解析结果，统计中会直接显示收到 9 条。

### Relevance score / 相关性分数

Every result row includes a `Score / 相关度` value. Use `:score <number>` to see the exact tokens, hit counts, and formula for that result.

每条结果都会显示 `Score / 相关度`。使用 `:score <编号>` 可以查看该结果的具体词元、命中数量和计算式。

```text
Score = (3 × number of query tokens matched in the title
         + number of query tokens matched in the snippet)
        / number of unique query tokens

分数 =（3 × 标题命中的查询词元数 + 摘要命中的查询词元数）
        ÷ 查询的不重复词元数
```

The theoretical range is **0–4**. It is a lightweight ranking index, not a probability, percentage, or neural semantic-similarity score. A score of zero does not delete a result.

理论范围是 **0–4**。它是轻量排序指数，不是概率、百分比，也不是神经网络语义相似度。即使分数为 0，结果也不会被删除。

Text is normalized and lowercased before matching. Latin and other word-based text uses Unicode word tokens. Chinese, Japanese, and Korean text additionally uses whole words, single characters, and adjacent two-character bigrams. Repeated occurrences of the same token count only once because matching uses sets.

匹配前会规范化文本并转为小写。拉丁字母等按词书写的文本使用 Unicode 词元；中日韩文本还会使用整词、单字和相邻二字词元。由于命中通过集合计算，同一个词元重复出现不会重复计分。

For example, with query `red apple`, title `red`, and snippet `apple`, there are two query tokens, one title hit, and one snippet hit: `(1 × 3 + 1 × 1) / 2 = 2.0`.

例如，查询为 `red apple`、标题为 `red`、摘要为 `apple` 时，共有两个查询词元，标题和摘要各命中一个，因此分数为 `(1 × 3 + 1 × 1) / 2 = 2.0`。

## 5. Search engines / 搜索引擎

### Start with no setup / 无需设置，直接使用

The default pool now searches Google, Bing, DuckDuckGo, Yahoo, Baidu, and Brave at the same time. You do not need to configure an engine before typing a query.

默认搜索池现在会同时使用 Google、Bing、DuckDuckGo、Yahoo、百度和 Brave。输入搜索内容前不需要配置引擎。

To see every available engine and your current pool:

查看全部引擎和当前搜索池：

```text
:pool
```

To restore the default pool at any time:

随时可用以下命令恢复默认搜索池：

```text
:pool reset
```

### Choose built-in engines / 选择内置引擎

Available names are:

可用名称如下：

```text
google, bing, duckduckgo, yahoo, yahoojp, baidu, brave,
ecosia, yandex, mojeek, sogou
```

Examples / 示例：

```text
:pool google
:pool google,bing,yahoo
:pool yahoojp
:pool bing,baidu,sogou
:pool google,ecosia,mojeek
```

Setting `:pool` replaces the current pool, so include every engine you want to use. If you normally use Google, Yahoo, Bing, DuckDuckGo, or Ecosia through Safari, choose the same engine name here; Safari itself is the browser rather than a separate search provider in this tool.

设置 `:pool` 会替换当前搜索池，因此需要列出所有想使用的引擎。如果你平时通过 Safari 使用 Google、Yahoo、Bing、DuckDuckGo 或 Ecosia，在这里选择对应名称即可；Safari 本身是浏览器，不是本工具中的独立搜索提供方。

### Add your own engine by domain / 通过域名添加自己的引擎

Type the domain directly after `:pool`. Do not edit the source code.

把域名直接写在 `:pool` 后面即可，不需要修改源代码。

```text
:pool yahoo.hk
:pool yahoo.co.jp
:pool google,yahoo.co.jp,baidu.com
:pool https://search.yahoo.co.jp
```

For Yahoo Japan alone, use `:pool yahoojp`. Its actual search endpoint is `search.yahoo.co.jp`. If you previously entered `yahoo.jp`, the program treats that as a Yahoo Japan alias, displays the corrected `yahoo.co.jp` name, and migrates the saved custom-engine entry.

仅使用雅虎日本时，可输入 `:pool yahoojp`。实际搜索地址为 `search.yahoo.co.jp`。如果此前输入过 `yahoo.jp`，程序会将其作为雅虎日本别名，显示更正后的 `yahoo.co.jp`，并迁移已保存的自定义引擎条目。

The built-in `:pool yahoo` is different: it requests only Yahoo Global at `search.yahoo.com`. A 5xx response causes one retry of that same address with the same query and page number. It never switches to Yahoo Japan. The Source column reads `yahoo.com`; if the global endpoint still fails, `:errors` reports that actual failure.

内置 `:pool yahoo` 的行为不同：它只请求全球入口 `search.yahoo.com`。收到 5xx 后，会使用相同查询和页码重试同一个地址，不会切换到雅虎日本。来源栏显示 `yahoo.com`；如果全球入口仍然失败，`:errors` 会报告这个真实失败。

Custom engines are saved automatically and appear under `Custom engines / 自定义引擎` the next time you run `:pool`.

自定义引擎会自动保存；下次输入 `:pool` 时，会显示在“Custom engines / 自定义引擎”一栏。

Enter a domain only, with an optional `http://` or `https://` prefix. The program recognizes several common search sites and otherwise tries a standard search address plus a general result parser. It follows redirects returned by the website. Apart from the explicitly documented `yahoo.jp` to `yahoo.co.jp` alias, it does not substitute a different regional engine on your behalf.

只需输入域名，也可以加上 `http://` 或 `https://` 前缀。程序会识别多个常见搜索网站；对于其他网站，会尝试常见的搜索地址和通用结果解析。网站自身返回跳转时，程序会跟随跳转。除了上面明确说明的 `yahoo.jp` 至 `yahoo.co.jp` 别名外，不会擅自替你换成其他地区的引擎。

A custom engine can still fail because of network access, regional availability, CAPTCHA checks, login requirements, or an unsupported page layout. This is reported as an engine failure; it does not stop the other engines.

自定义引擎仍可能因网络连接、地区可用性、验证码、登录要求或网页结构不受支持而失败。程序会显示该引擎失败，但不会影响其他引擎。

### SearXNG: optional; most people can skip it / SearXNG：可选项，大多数人可跳过

**You do not need SearXNG. If you do not already use it, ignore this subsection and no address configuration is needed.**

**你不需要安装或配置 SearXNG。如果你本来就没有使用它，直接跳过本小节即可，也不需要填写任何地址。**

Only if you already have a running SearXNG service, you can add it like any other engine:

只有已经运行 SearXNG 服务的人，才需要像下面这样把它加入搜索池：

```text
:pool searxng
:pool bing,searxng
```

If it does not connect, use `:pool reset` and continue with the normal engines.

如果无法连接，输入 `:pool reset`，继续使用普通搜索引擎即可。

### Network availability / 网络可用性

Any search engine may be unreachable on a particular network. A failed, timed-out, CAPTCHA-blocked, or unreadable engine is listed in a warning while the remaining engines can still return results.

任何搜索引擎都可能在特定网络下无法连接。失败、超时、被验证码拦截或无法解析的引擎会显示在警告中，其他引擎仍可正常返回结果。

Use `:errors` after a search to distinguish DNS failure, connection timeout, HTTP 429 rate limiting, other HTTP errors, CAPTCHA/security verification, consent pages, explicit no-results responses, and unrecognized result layouts. For a returned web page, the diagnostic includes its HTTP status, title, and final URL after redirects. A layout error is no longer described as proof that there are no more results.

搜索后使用 `:errors` 可以区分域名解析失败、连接超时、HTTP 429 限流、其他 HTTP 错误、验证码／安全验证、同意页、网站明确返回无结果，以及结果布局无法识别。对于已经返回的网页，诊断会显示 HTTP 状态、网页标题和跳转后的最终地址。布局无法识别不再被当作“没有更多结果”的确定证据。

#### Optional network proxies / 可选网络代理

Try a direct connection first; a proxy is optional rather than a general requirement. For example, while working on a HiMCM project in Hong Kong, you might want to compare sources or search visibility through a US network exit to gain another information perspective. A proxy may help with that region-specific comparison, but it does not guarantee more detailed or accurate information. If you choose to use one, the program's static engine requests use Python `requests`, which respects the standard `HTTP_PROXY` and `HTTPS_PROXY` environment variables. Set them before launching, replacing the uppercase placeholders with your own proxy client's host and port; do not copy another machine's port.

请先尝试直连；代理是可选项，不是通用要求。例如，在香港参加 HiMCM 项目时，你可能希望通过美国网络出口比较资料来源或搜索结果的可见性，以获得另一种信息视角。代理可能有助于这种按地区比较，但不保证信息一定更详尽或更准确。如果你选择使用代理，本程序的静态引擎请求会通过 Python `requests` 读取标准的 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。请在启动前设置，并将大写占位符替换成你自己的代理客户端地址和端口；不要照搬其他机器的端口。

macOS / macOS 终端：

```bash
HTTPS_PROXY=http://PROXY_HOST:PROXY_PORT HTTP_PROXY=http://PROXY_HOST:PROXY_PORT .tsearch-venv/bin/python tsearch.py
```

Windows PowerShell / Windows PowerShell 终端：

```powershell
$env:HTTPS_PROXY = "http://PROXY_HOST:PROXY_PORT"
$env:HTTP_PROXY = "http://PROXY_HOST:PROXY_PORT"
.tsearch-venv\Scripts\python.exe tsearch.py
```

These variables configure only the program's static requests. They do not configure proxy settings for Safari, Edge, or the optional Chromium fallback. If a browser fallback also needs a proxy, configure the operating system or that browser separately. A proxy changes the network route; it does not guarantee access, a particular search region, or exemption from CAPTCHA and consent checks.

这些变量只配置程序的静态请求，不会为 Safari、Edge 或可选 Chromium 回退设置代理。如果浏览器回退也需要代理，请另行配置操作系统或对应浏览器。代理只会改变网络路径，不保证一定能够访问、获得特定地区的搜索结果，也不保证免于验证码或同意确认。

### Why a browser can work when static parsing fails / 为什么浏览器能用而程序可能无法解析

The program requests a search endpoint and parses the returned HTML; it is not reading the page currently displayed by Safari, Chrome, or another browser. A browser may already have cookies, execute JavaScript, complete a consent flow or CAPTCHA, and receive a different HTML layout. An HTTP 200 response only means that a page arrived—it does not prove that the page contains search results.

程序会请求搜索入口并解析返回的 HTML，并不是读取 Safari、Chrome 等浏览器当前显示的画面。浏览器可能已有 Cookie、能够执行 JavaScript、已经完成同意流程或验证码，并收到不同的 HTML 布局。HTTP 200 只表示收到了网页，并不能证明网页中有搜索结果。

The revised program handles readable desktop, mobile, basic-HTML, and Lite layouts where possible and retries the documented alternate endpoints listed above. It does not bypass CAPTCHA or consent checks. When those are returned, `:errors` now says so explicitly instead of pretending that the engine had no results.

新版会尽量兼容可读的桌面版、移动版、基本 HTML 和 Lite 布局，并尝试上面列出的备用入口，但不会绕过验证码或同意确认。网站返回这些验证页时，`:errors` 会明确说明，不再假装引擎没有搜索结果。

### Real browser fallback / 真实浏览器回退

For Google on macOS, `:browser safari` is the same-session option described in section 2D. It does not create a separate browser profile: Safari opens the original Google URL, and the program reads the dedicated tab after rendering. Source reads `safari:google`. Automation and JavaScript permissions are still required, and no CAPTCHA is solved automatically.

对于 macOS 上的 Google，`:browser safari` 是 2D 节所述的同会话选项。它不会创建独立浏览器配置，而是由 Safari 打开原 Google 地址，再由程序读取专用标签页的渲染内容，来源显示 `safari:google`。仍需授予自动化和 JavaScript 权限，且不会自动破解验证码。

For Google on Windows, `:browser edge` uses the installed Edge described in section 2E and does not download Chromium. It uses a dedicated persistent Edge profile rather than your everyday profile. Source reads `edge:google`.

对于 Windows 上的 Google，`:browser edge` 会使用 2E 节所述的已安装 Edge，不下载 Chromium。它使用独立持久的 Edge 配置，而不是你的日常配置，来源显示 `edge:google`。

For the independent Chromium option, install the optional components in section 2C and enter `:browser on`. When a static engine fails, the program opens that engine's original search URL in Chromium and parses the rendered DOM after JavaScript runs. It uses one browser sequentially rather than launching one browser per failed engine. Results obtained this way have a Source value such as `browser:google`, `browser:ddg-html`, or `browser:yahoo.com`.

如需独立 Chromium 方案，请按照 2C 节安装可选组件并输入 `:browser on`。静态引擎失败时，程序会在 Chromium 中打开该引擎的原搜索地址，并在 JavaScript 执行后解析渲染完成的 DOM。多个失败引擎会顺序使用同一个浏览器，不会每个引擎都启动一个浏览器。通过此方式取得的结果，来源会显示为 `browser:google`、`browser:ddg-html` 或 `browser:yahoo.com` 等。

The browser profile is stored separately in `.tsearch-browser-profile` in your home directory. It preserves cookies between runs but does not read, copy, or modify your Safari, Chrome, or Edge personal profile. If a CAPTCHA or consent page appears, complete it yourself in the opened Chromium window; the program waits up to 90 seconds. It does not automatically solve CAPTCHA.

浏览器配置独立保存在主目录的 `.tsearch-browser-profile` 中，可在多次运行间保留 Cookie，但不会读取、复制或修改你的 Safari、Chrome 或 Edge 个人配置。如果出现验证码或同意页，需要你在打开的 Chromium 窗口中亲自完成，程序最多等待 90 秒，不会自动破解验证码。

HTTP 429 responses are not retried through Chromium. Browser rendering also cannot guarantee access when the network is unreachable or the website continues to return HTTP 500. In those cases, `:errors` retains both the static and browser failure details. Use `:browser off` to return to static-only operation.

HTTP 429 不会通过 Chromium 再次请求。网络无法连接或网站持续返回 HTTP 500 时，浏览器渲染也不能保证成功；此时 `:errors` 会同时保留静态请求和浏览器回退的失败详情。输入 `:browser off` 可恢复仅静态请求模式。

## 6. Troubleshooting / 故障排查

All troubleshooting has moved to **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**. Run `:errors` for engine diagnostics. For Safari, run `:browser check`; if it fails, run `:browser setup` and follow the displayed steps.

全部故障排查内容已移至 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**。引擎问题请运行 `:errors`；Safari 问题请运行 `:browser check`，若失败再运行 `:browser setup` 并按提示操作。
