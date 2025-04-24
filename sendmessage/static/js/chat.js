document.addEventListener("DOMContentLoaded", function () {
    const socket = io();
socket.on("new_conv",()=>{updateConversations()})
    const chatBox = document.getElementById("chat-box");
    const form = document.getElementById("chat-form");
    const textarea = form.querySelector("textarea");
    const fileInput = form.querySelector('input[name="file"]');

    const conversationId = chatBox.dataset.conversationId;
    const senderId = parseInt(chatBox.dataset.senderId);
    const partnerId = parseInt(chatBox.dataset.partnerId);
    const partnerName = chatBox.dataset.partnerName || "Đối phương";

    const currentUserAvatar = document.querySelector('.card-header').nextElementSibling.querySelector('img')?.src || '/static/default-avatar.png';
    const partnerAvatar = document.querySelector('.card-header img')?.src || '/static/default-avatar.png';

    socket.emit('join', { room: conversationId });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const content = textarea.value.trim();
        const file = fileInput.files[0];

        if (!content && !file) return;

        // Trường hợp gửi file
        if (file) {
            // Hiển thị thông báo đang tải
            const loadingId = 'loading-' + Date.now();
            appendLoadingMessage(loadingId);

            const formData = new FormData();
            formData.append("file", file);
            formData.append("sender_id", senderId);
            formData.append("conversation_id", conversationId);

            // Nếu có nội dung kèm theo file
            if (content) {
                formData.append("content", content);
                textarea.value = "";
            }

            try {
                const response = await fetch("/send-message-with-file", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();

                // Xóa thông báo đang tải
                removeLoadingMessage(loadingId);

                // Reset form
                fileInput.value = "";
                document.getElementById('selected-filename').textContent = 'Chưa chọn file';

                if (data.status !== "success") {
                    alert("Có lỗi xảy ra khi gửi file. Vui lòng thử lại!");
                }
            } catch (error) {
                console.error("Lỗi khi gửi tin nhắn với file:", error);
                removeLoadingMessage(loadingId);
                alert("Lỗi khi gửi tin nhắn với file. Vui lòng thử lại!");
            }
        }
        // Trường hợp chỉ gửi văn bản
        else if (content) {
            socket.emit("send_message", {
                content: content,
                sender_id: senderId,
                conversation_id: conversationId,
                partner_id: partnerId
            });

            textarea.value = "";
            textarea.style.height = 'auto';
        }
    });

    socket.on("receive_message", function (data) {
        const isSender = parseInt(data.sender_id) === senderId;

        // Nếu tin nhắn có attachment
        if (data.has_attachment) {
            appendMessageWithAttachment(
                data.content,
                data.sender_id,
                isSender ? 'Bạn' : partnerName,
                isSender,
                data.file_url,
                data.file_type,
                data.original_filename,
                data.file_size
            );
        } else {
            // Tin nhắn thông thường
            appendMessage(data.content, data.sender_id, isSender ? 'Bạn' : partnerName, isSender);
        }
    });

    function appendLoadingMessage(id) {
        const loadingHtml = `
            <div id="${id}" class="mb-3 d-flex justify-content-end">
                <div style="max-width: 70%;">
                    <div class="message-bubble rounded-3 p-2 bg-primary text-white" style="border-radius: 18px;">
                        <div class="d-flex align-items-center">
                            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                            <span>Đang tải file...</span>
                        </div>
                    </div>
                </div>
                <img src="${currentUserAvatar}" alt="Avatar" class="rounded-circle ms-2 align-self-end" width="30" height="30">
            </div>
        `;
        chatBox.insertAdjacentHTML("beforeend", loadingHtml);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function removeLoadingMessage(id) {
        const loadingElement = document.getElementById(id);
        if (loadingElement) {
            loadingElement.remove();
        }
    }

    function appendMessage(content, sender_id, senderName, isOwnMessage) {
        const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const currentDate = new Date().toLocaleDateString('vi-VN');
        const avatar = isOwnMessage ? currentUserAvatar : partnerAvatar;

        let contentHTML = `<p class="mb-0">${content}</p>`;

        const msgHtml = `
            <div class="mb-3 ${isOwnMessage ? 'd-flex justify-content-end' : 'd-flex justify-content-start'}">
                ${!isOwnMessage ? `<img src="${avatar}" alt="Avatar" class="rounded-circle me-2 align-self-end" width="30" height="30">` : ''}

                <div style="max-width: 70%;">
                    ${!isOwnMessage ? `<small class="text-muted mb-1 d-block">${senderName}</small>` : ''}

                    <div class="message-bubble rounded-3 p-2 ${isOwnMessage ? 'bg-primary text-white' : 'bg-light'}" style="border-radius: 18px; display: inline-block;">
                        ${contentHTML}
                    </div>

                    <small class="text-muted d-block mt-1">${currentTime} ${currentDate}</small>
                </div>

                ${isOwnMessage ? `<img src="${avatar}" alt="Avatar" class="rounded-circle ms-2 align-self-end" width="30" height="30">` : ''}
            </div>
        `;

        chatBox.insertAdjacentHTML("beforeend", msgHtml);
        requestAnimationFrame(() => {
            chatBox.scrollTop = chatBox.scrollHeight;
        });
    }

    function appendMessageWithAttachment(content, sender_id, senderName, isOwnMessage, fileUrl, fileType, originalFilename,fileSize) {
        const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const currentDate = new Date().toLocaleDateString('vi-VN');
        const avatar = isOwnMessage ? currentUserAvatar : partnerAvatar;

        // Xử lý hiển thị nội dung tin nhắn
        let contentHTML = "";
        if (content && content.trim() !== "") {
            contentHTML = `<p class="mb-2">${content}</p>`;
        }

        // Xử lý hiển thị attachment
        let attachmentHTML = "";
        if (fileUrl) {
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileType.toLowerCase())) {
                // Hiển thị hình ảnh
                attachmentHTML = `
                    <div class="mt-2 position-relative">
                        <img src="${fileUrl}" class="img-fluid rounded" style="max-width: 100%; max-height: 300px;" alt="${originalFilename}">
                        <a href="${fileUrl}?fl_attachment=${encodeURIComponent(originalFilename)}"
                           download="${originalFilename}"
                           class="btn btn-sm btn-light position-absolute bottom-0 end-0 m-2"
                           title="Tải xuống ${originalFilename}">
                            <i class="fa fa-download"></i>
                        </a>
                    </div>
                `;
            } else {
                // Hiển thị các loại file khác
                let fileIcon = 'fa-file';
                if (["doc", "docx"].includes(fileType)) fileIcon = 'fa-file-word text-primary';
                else if (["xls", "xlsx"].includes(fileType)) fileIcon = 'fa-file-excel text-success';
                else if (["ppt", "pptx"].includes(fileType)) fileIcon = 'fa-file-powerpoint text-warning';
                else if (fileType === 'pdf') fileIcon = 'fa-file-pdf text-danger';
                else if (["zip", "rar", "7z"].includes(fileType)) fileIcon = 'fa-file-archive text-secondary';
                else if (["txt"].includes(fileType)) fileIcon = 'fa-file-alt text-info';
                else if (["cpp", "c", "py", "js", "html", "css", "php", "java"].includes(fileType)) fileIcon = 'fa-file-code text-dark';

                attachmentHTML = `
                    <div class="file-attachment d-flex align-items-center p-2 border rounded-3 mt-2 bg-white">
                        <i class="fa ${fileIcon} me-2"></i>
                        <a href="${fileUrl}"
                           target="_blank"
                           class="text-decoration-none text-truncate ${isOwnMessage ? 'text-dark' : ''}"
                           style="max-width: 200px;"
                           title="${originalFilename}">
                            ${originalFilename || 'Tải xuống'}
                        </a>
                        <small class="ms-auto text-muted">
                            ${fileSize ? `${(parseInt(fileSize) / 1024).toFixed(1)} KB` : ''}
                        </small>
                    </div>
                `;
            }
        }

        const msgHtml = `
            <div class="mb-3 ${isOwnMessage ? 'd-flex justify-content-end' : 'd-flex justify-content-start'}">
                ${!isOwnMessage ? `<img src="${avatar}" alt="Avatar" class="rounded-circle me-2 align-self-end" width="30" height="30">` : ''}

                <div style="max-width: 70%;">
                    ${!isOwnMessage ? `<small class="text-muted mb-1 d-block">${senderName}</small>` : ''}

                    <div class="message-bubble rounded-3 p-2 ${isOwnMessage ? 'bg-primary text-white' : 'bg-light'}" style="border-radius: 18px; display: inline-block;">
                        ${contentHTML}
                        ${attachmentHTML}
                    </div>

                    <small class="text-muted d-block mt-1">${currentTime} ${currentDate}</small>
                </div>

                ${isOwnMessage ? `<img src="${avatar}" alt="Avatar" class="rounded-circle ms-2 align-self-end" width="30" height="30">` : ''}
            </div>
        `;

        chatBox.insertAdjacentHTML("beforeend", msgHtml);
        requestAnimationFrame(() => {
            chatBox.scrollTop = chatBox.scrollHeight;
        });
    }

    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';

        const maxHeight = 150;
        if (this.scrollHeight > maxHeight) {
            this.style.height = maxHeight + 'px';
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
    });

    chatBox.scrollTop = chatBox.scrollHeight;
});