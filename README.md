# 葡萄牙找房

Windows 桌面工具：按地区/关键词采集葡萄牙房产网站，并把结果写入 Google 表格。

- 房源网站结果写入工作表「找房子」
- 勾选 Google 地图并填写关键词，按「工作表1」商家格式自动登记

## 安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 运行

```powershell
python property_scraper_gui.py
```

或双击 `start_property_scraper_gui.bat`。

凭证文件（`oauth_client.json`、`drive_token.json`、`service_account.json`、`app_settings.json`）请放在本机程序目录，不要提交到仓库。

## 下载已发布版本

当前正式包由 GitHub Actions 自动构建并签名：

- Release：https://github.com/secure-artifacts/portugal-find-house/releases/tag/v0.1.1
- Windows 安装包：https://github.com/secure-artifacts/portugal-find-house/releases/download/v0.1.1/portugal-find-house-v0.1.1.exe

下载后把本机的 `oauth_client.json`、`drive_token.json`、`service_account.json`、`app_settings.json` 放到 exe 同一目录再运行。不要把这些文件提交到仓库。

## 如何发布新版本

本项目使用 GitHub Actions 自动构建和发布。每次发布新版本只需要创建一个 Git Tag 并推送即可。

### 发布步骤

#### 1. 确保代码已提交并推送

在发布之前，确保你的所有代码改动已经提交并推送到 GitHub：

```bash
# 查看当前状态
git status

# 添加所有改动
git add .

# 提交改动（把"你的改动说明"替换成实际的描述）
git commit -m "你的改动说明"

# 推送到 GitHub
git push origin main
```

#### 2. 创建版本 Tag

Git Tag 是一个版本标记，用于标识发布的版本号。版本号格式为 `v主版本.次版本.修订版本`，例如 `v1.0.0`、`v1.1.0`、`v2.0.0`。

```bash
# 创建一个新的版本 tag（将 v1.0.1 替换为你想要的版本号）
git tag -a v1.0.1 -m "Release version 1.0.1"
```

#### 3. 推送 Tag 触发自动构建

```bash
# 推送 tag 到 GitHub（这会自动触发 CI 构建）
git push origin v1.0.1
```

推送后，GitHub Actions 会自动执行以下操作：

1. 构建项目
2. 生成安全签名（Attestation）
3. 创建 Release 并上传构建产物

#### 4. 查看构建结果

- 构建进度：访问项目的 **Actions** 页面查看
- 发布结果：访问项目的 **Releases** 页面查看已发布的文件

### 版本号说明

| 版本号格式 | 什么时候用 | 示例 |
|-----------|-----------|------|
| `vX.0.0` | 重大更新、不兼容改动 | `v2.0.0` |
| `vX.Y.0` | 新增功能 | `v1.1.0` |
| `vX.Y.Z` | 修复 bug | `v1.0.1` |

### 如果构建失败怎么办

1. 访问项目的 **Actions** 页面查看错误日志
2. 修复代码问题
3. 删除失败的 tag 并重新创建：

```bash
# 删除本地 tag
git tag -d v1.0.1

# 删除远程 tag
git push origin :refs/tags/v1.0.1

# 修复问题后，重新创建并推送
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
```

注意：不要在 GitHub 网页上手动创建或替换 Release 文件。平台会检查上传者必须是 `github-actions[bot]`。

---

# 葡萄牙房源采集脚本说明

脚本文件：`portugal_property_scraper.py`

它会根据你填写的地区和筛选条件，尝试查询这些葡萄牙房地产网站：

- idealista.pt
- remax.pt
- imovirtual.com
- predimed.pt
- supercasa.pt
- kyero.com
- portadafrente.com
- Google 地图 / Google 搜索房地产结果（`google_maps`）

导出的 CSV 表格字段包括：

- `source`：来源网站
- `name`：名称
- `info`：房源信息
- `contact`：联系方式，只有页面公开显示时才能抓到
- `url`：房源网址
- `photo_cloud_folder`：照片上传到 Google Drive 后的云端文件夹地址
- `photo_local_folder`：本地照片文件夹
- `price`：价格
- `rooms`：房间数
- `area`：面积
- `location`：地区
- `image_count`：照片数量

同时，脚本默认会把数据追加写入这个 Google Sheet：

```text
表格 ID：1o1aJOU63NTO582H0xkK1JRnVyBi1pE7GwpqPvXq5-dM
工作表名：找房子
```

照片默认上传到这个 Google Drive 父文件夹，并且每个房源自动创建一个独立子文件夹：

```text
1cAud70i5ttESqM79m9JdiT9nNPyT82g0
```

## 1. 推荐保存路径

你说以后脚本路径想放到：

```powershell
E:\Codex
```

建议目录结构：

```text
E:\Codex\
  portugal_property_scraper.py
  oauth_client.json
  drive_token.json
  service_account.json
  outputs\
    portugal_properties.csv
    property_photos\
```

## 2. 基础运行：只导出表格和本地照片

进入脚本目录：

```powershell
cd E:\Codex
```

查找 Mafra，买房，至少 T3，面积至少 100 平方米，最多采集 30 条：

```powershell
python portugal_property_scraper.py --area Mafra --deal sale --min-rooms 3 --min-area 100 --max-listings 30
```

输出文件默认是：

```text
outputs\portugal_properties.csv
```

照片默认保存到：

```text
outputs\property_photos
```

## 3. 指定地区和网站

只查 idealista、imovirtual、supercasa：

```powershell
python portugal_property_scraper.py --area Loures --sites idealista imovirtual supercasa --min-rooms 4 --min-area 150
```

租房：

```powershell
python portugal_property_scraper.py --area Lisboa --deal rent --min-rooms 2
```

## 4. 更稳的方法：粘贴搜索页或房源页

有些网站会改版或拦截自动搜索。你可以先在浏览器打开网站，手动筛选地区、房间、面积，然后复制搜索结果页链接给脚本：

```powershell
python portugal_property_scraper.py --area Mafra --seed-url "https://www.idealista.pt/comprar-casas/mafra/" --seed-url "https://www.imovirtual.com/pt/resultados/comprar/casa/mafra"
```

也可以直接放单个房源页：

```powershell
python portugal_property_scraper.py --area Mafra --seed-url "https://www.idealista.pt/zh/imovel/34317223/"
```

如果只想采集你粘贴的链接，不自动跑其他网站：

```powershell
python portugal_property_scraper.py --area Mafra --no-auto-search --seed-url "https://www.idealista.pt/zh/imovel/34317223/"
```

## 5. 上传照片到 Google Drive

脚本支持把每个房源照片上传到 Google Drive，并把云端文件夹地址写入 CSV 的 `photo_cloud_folder`。

准备步骤：

1. 在 Google Cloud Console 建一个 OAuth Desktop App。
2. 下载 OAuth 客户端文件，改名为 `oauth_client.json`。
3. 把 `oauth_client.json` 放到脚本同目录。
4. 第一次运行时会打开浏览器，让你登录 Google 授权。
5. 授权后会生成 `drive_token.json`，以后不用重复登录。

运行命令：

```powershell
python portugal_property_scraper.py --area Mafra --min-rooms 3 --min-area 100 --upload-drive
```

推荐默认组合：

- Google Drive 上传照片：使用 `drive_token.json` 里的 OAuth 授权，这样使用你的 Google Drive 存储空间。
- Google Sheet 写入：使用 `service_account.json`，只要表格共享给服务账号即可稳定写入。

如果强制使用服务账号上传到普通 My Drive，Google 可能会报“服务账号没有存储配额”。除非你使用 Shared Drive，否则不建议这样做。

如果你确实要强制两边都使用服务账号，确保目标 Google Drive 文件夹和 Google Sheet 都已经共享给 `service_account.json` 里的 `client_email`，然后运行：

```powershell
python portugal_property_scraper.py --area Mafra --upload-drive --auth-mode service-account --drive-parent-folder-id "你的GoogleDrive文件夹ID"
```

如果你已经有一个 Google Drive 父文件夹，可以复制该文件夹 ID，然后这样运行：

```powershell
python portugal_property_scraper.py --area Mafra --upload-drive --drive-parent-folder-id "你的GoogleDrive文件夹ID"
```

如果只想导出本地 CSV，不写入 Google Sheet：

```powershell
python portugal_property_scraper.py --area Mafra --no-write-sheet
```

## 6. 常见问题

### 联系方式为空

很多网站把电话隐藏在按钮后面，或者要求登录后才显示。脚本只能抓取页面 HTML 里公开可见的电话、邮箱、`tel:` 和 `mailto:`。

### 搜索结果很少

建议用 `--seed-url`，把你在浏览器里筛选好的搜索结果页复制进去。这样比脚本猜网站搜索 URL 稳定。

### CSV 打开乱码

脚本使用 `utf-8-sig` 保存，Excel 一般可以正常识别中文和葡萄牙语。如果仍乱码，用 Excel 的“数据 -> 自文本/CSV”导入，编码选择 UTF-8。

### 网站返回 403 或验证码

这些网站有反爬。不要用普通 HTTP 硬刷，按下面顺序处理：

1. 先登录账号，保存浏览器 Cookie。
2. 用真实 Chrome 采集，不要关浏览器窗口。
3. 遇到验证码时，在弹出的 Chrome 里手动完成，脚本会等你。

推荐流程：

```powershell
# 1. 先打开登录页，在弹出的 Chrome 里登录 Idealista / Google / Imovirtual
python portugal_property_scraper.py --login --sites idealista imovirtual google_maps --browser-visible

# 2. 再用同一个浏览器资料目录开始找房
python portugal_property_scraper.py --area Coimbra --deal rent --sites idealista google_maps --browser-backend cdp --browser-visible
```

也可以双击 `start_chrome_for_login.bat`，先在真实 Chrome 里登录，然后在 GUI 的 CDP 栏填：

```text
http://127.0.0.1:9222
```

GUI 里对应按钮：

- `登录选中网站账号`
- `使用真实 Chrome（推荐，反爬更稳）`

如果只是临时被拦，也可以降低速度：

```powershell
python portugal_property_scraper.py --area Mafra --pause 4
```

也可以只用 `--seed-url` 采集你已经在浏览器里打开过的搜索页。

## 7. 谷歌地图房地产搜索

勾选 `google_maps` 后，脚本会同时打开：

- Google 地图：`casas à venda em 地区 Portugal` 或 `casas para arrendar em 地区 Portugal`
- Google 搜索里的房产结果，并尽量抽出 Idealista / Imovirtual 等外链

例：

```powershell
python portugal_property_scraper.py --area Coimbra --deal rent --sites google_maps --max-listings 20 --no-write-sheet
```

地图结果会写入 CSV，`source` 为 `google_maps`。如果卡片上带有 Idealista 等房源链接，会按普通房源页继续采集。

Google 地图是动态页面，必须开浏览器。建议同时登录 Google 账号，结果更稳定。

## 8. 参数速查

```text
--area                 地区，例如 Mafra、Loures、Lisboa
--deal                 sale 或 rent
--sites                网站列表，例如 idealista imovirtual supercasa
--min-rooms            最少房间数
--max-rooms            最多房间数
--min-area             最小面积，单位 m2
--max-area             最大面积，单位 m2
--max-listings         最多采集房源数
--seed-url             手动添加搜索页或房源页，可重复使用
--no-auto-search       只使用手动添加的 --seed-url，不自动生成搜索页
--output               CSV 输出路径
--photo-dir            本地照片目录
--no-photos            不下载照片
--upload-drive         上传照片到 Google Drive
--auth-mode            强制 Drive 和 Sheet 都使用 oauth 或 service-account
--drive-auth-mode      Drive 上传授权方式，默认 oauth
--sheet-auth-mode      Sheet 写入授权方式，默认 service-account
--google-credentials   Google OAuth 客户端 JSON 路径，默认 oauth_client.json
--google-token         Google token 保存路径，默认 drive_token.json
--service-account      Google 服务账号 JSON 路径，默认 service_account.json
--drive-parent-folder-id Google Drive 父文件夹 ID
--sheet-id             Google Sheet 表格 ID
--sheet-name           工作表名字，默认 找房子
--no-write-sheet       不写入 Google Sheet，只保存本地 CSV
--pause                请求间隔秒数
--browser-mode         fallback / always / off
--browser-backend      cdp=真实 Chrome（推荐） / playwright
--cdp-url              连接到已打开的 Chrome，例如 http://127.0.0.1:9222
--login                只打开登录页，让你手动登录并保存 Cookie
--browser-visible      显示浏览器窗口，验证码时必须开
--browser-profile      浏览器 Cookie/登录状态保存目录
--browser-wait-seconds 遇到验证时最多等待秒数
```
