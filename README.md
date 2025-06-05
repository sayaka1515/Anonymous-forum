匿名論壇
一個使用 Flask 開發的簡單匿名論壇，支援用戶註冊、貼文發布和討論版管理。
必要條件
在本地運行專案之前，請確保已安裝以下軟體：

**1.python版本**
----------------------------------------
Python：版本 3.7 或更高（推薦 3.9+）
Git：用於克隆倉庫
pip：Python 套件管理器（通常隨 Python 一起安裝）
虛擬環境：可選但推薦，用於隔離依賴

可選工具

程式碼編輯器（例如 VSCode、PyCharm）
SQLite 瀏覽器（例如 DB Browser for SQLite）用於檢查 forum.db

安裝步驟
按照以下步驟設置並運行專案：

克隆倉庫
git clone https://github.com/sayaka1515/Anonymous-forum.git


將專案下載到本地電腦。


進入專案目錄
cd Anonymous-forum


切換到 Anonymous-forum 目錄。


創建虛擬環境
python -m venv venv


創建名為 venv 的虛擬環境，用於隔離依賴。
在 Windows 上使用 python（若失敗可嘗試 py）；在 macOS/Linux 上可能需要使用 python3。


啟用虛擬環境

Windows：venv\Scripts\activate


macOS/Linux：source venv/bin/activate


啟用後，終端機提示符應顯示 (venv)。


安裝依賴
pip install -r requirements.txt


安裝 requirements.txt 中列出的所有 Python 套件。
確保倉庫中包含 requirements.txt，若無，需在本地生成（pip freeze > requirements.txt）並提交。


運行應用程式
python app.py


啟動 Flask 伺服器。
打開瀏覽器，訪問 http://localhost:5000 查看論壇。
伺服器以調試模式運行，按 Ctrl + C 停止。



使用方法

初始設置：首次運行會創建 forum.db，包含預設討論版和管理員用戶（yukari17，密碼：admin123）。
功能：
註冊新用戶或使用管理員帳號登入。
創建貼文、上傳媒體（png、jpg、jpeg、gif、mp4），管理員可管理討論版。


注意事項：
媒體檔案儲存於 static/uploads/。
日誌記錄在 forum.log 中，供調試使用。



疑難排解

命令未找到：確認 Python 和 Git 已添加到系統 PATH。若使用可攜式版本，手動調整 PATH（例如 set PATH=%PATH%;D:\PortablePython）。
端口衝突：若 python app.py 失敗，可能端口 5000 被占用。編輯 app.run(debug=True) 為 app.run(debug=True, port=5001)。
缺少依賴：檢查 requirements.txt 是否包含所有套件（例如 flask、flask-sqlalchemy、flask-login）。
