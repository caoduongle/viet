# Data Model & State Lifecycle: 025 — Sửa lỗi CI Kiểm Thử Tự Động

## 1. Mô hình Môi trường Phục vụ Kiểm thử Cách ly (E2E Test Environment)

```mermaid
stateDiagram-v2
    [*] --> InitTmpDist: mkdtempSync(os.tmpdir())
    InitTmpDist --> BuildInitial: runBuildWeb(tmpDist)
    BuildInitial --> StartChildServer: spawn(node serve.mjs, PORT=8101, DIST=tmpDist)
    StartChildServer --> WaitServer: waitForServer(http://localhost:8101)
    WaitServer --> RunInitialTest: Browser goto(http://localhost:8101) & check SW
    RunInitialTest --> MutateSource: Sửa app.js với token duy nhất
    MutateSource --> RebuildToTmp: runBuildWeb(tmpDist)
    RebuildToTmp --> TriggerSWUpdate: registration.update() & reload()
    TriggerSWUpdate --> AssertNewContent: verify token & new cache
    AssertNewContent --> Cleanup: Finally Block
    Cleanup --> RevertAppJs: fs.writeFileSync(originalAppJs)
    Cleanup --> KillServer: server.kill()
    Cleanup --> RemoveTmpDist: fs.rmSync(tmpDist)
    RevertAppJs --> [*]
    KillServer --> [*]
    RemoveTmpDist --> [*]
```

### Các thuộc tính trạng thái:
- **`SW_PORT`**: Số cổng dành riêng cho test update SW, cố định là `8101`.
- **`SW_ORIGIN`**: `http://localhost:8101`.
- **`tmpDist`**: Đường dẫn thư mục tạm thời trên hệ thống tệp, được sinh bởi `fs.mkdtempSync("viet-sw-dist-")`.
- **`server`**: Thực thể tiến trình con `ChildProcess` chạy máy chủ `serve.mjs`.
- **`uniqueToken`**: Chuỗi bình luận duy nhất `/* SW_UPDATE_TEST_<timestamp> */` để xác nhận nội dung thực tế được tải lại qua mạng/SW.

---

## 2. Mô hình Tương tác Hộp thoại Chọn Bộ Ký tự (GUI Tkinter)

```mermaid
sequenceDiagram
    participant User/Test
    participant TeachTab
    participant Dialog as Toplevel Dialog
    participant Controller as AppController

    User/Test->>TeachTab: add_seed()
    TeachTab->>Dialog: Khởi tạo Toplevel("Chọn bộ ký tự")
    Note over Dialog: Hiển thị Radiobutton ("Cơ bản", "Toán...", ...)<br/>và các nút "Nạp ký tự", "Huỷ"
    
    alt Người dùng bấm "Nạp ký tự"
        User/Test->>Dialog: invoke() nút "Nạp ký tự"
        Dialog->>Controller: get_missing_chars("co_ban", exclude=queue)
        Controller-->>Dialog: Danh sách ký tự còn thiếu
        Dialog->>TeachTab: Bổ sung ký tự vào tab.queue
        Dialog->>User/Test: messagebox.showinfo("Đã nạp...")
        Dialog->>Dialog: destroy()
    else Người dùng bấm "Huỷ"
        User/Test->>Dialog: invoke() nút "Huỷ"
        Dialog->>Dialog: destroy()
        Note over TeachTab: tab.queue giữ nguyên không đổi
    end
```
