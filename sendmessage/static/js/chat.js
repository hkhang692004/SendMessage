document.addEventListener("DOMContentLoaded", function () {
    const socket = io();

    const chatBox = document.getElementById("chat-box");
    const form = document.getElementById("chat-form");
    const textarea = form.querySelector("textarea");
    const fileInput = form.querySelector('input[name="file"]');

    const conversationId = chatBox.dataset.conversationId;
    const senderId = parseInt(chatBox.dataset.senderId);
    const partnerId = parseInt(chatBox.dataset.partnerId);
    const partnerName = chatBox.dataset.partnerName || "Đối phương";

    // Lấy URL avatar của người dùng và đối tác
    const currentUserAvatar = document.querySelector('.card-header').nextElementSibling.querySelector('img')?.src || '/static/default-avatar.png';
    const partnerAvatar = document.querySelector('.card-header img')?.src || '/static/default-avatar.png';

    socket.emit('join', { room: conversationId });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const content = textarea.value.trim();
        const file = fileInput.files[0];

        if (!content && !file) return;

        // Gửi file nếu có
        if (file) {
            // Hiển thị thông báo đang tải
            const loadingId = 'loading-' + Date.now();
            appendLoadingMessage(loadingId);

            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch("/upload", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();
                const fileUrl = data.url;

                // Xóa thông báo đang tải
                removeLoadingMessage(loadingId);

                // Gửi URL file qua socket
                socket.emit("send_message", {
                    content: fileUrl,
                    sender_id: senderId,
                    conversation_id: conversationId
                });

                fileInput.value = "";
            } catch (error) {
                console.error("Lỗi khi tải file:", error);
                // Xóa thông báo đang tải
                removeLoadingMessage(loadingId);
                alert("Lỗi khi tải file lên. Vui lòng thử lại!");
            }
        }

        // Gửi nội dung văn bản nếu có
        if (content) {
            socket.emit("send_message", {
                content: content,
                sender_id: senderId,
                conversation_id: conversationId
            });

            textarea.value = "";
        }
    });

    socket.on("receive_message", function (data) {
        const isSender = parseInt(data.sender_id) === senderId;
        appendMessage(data.content, data.sender_id, isSender ? 'Bạn' : partnerName, isSender);
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

        // Xác định loại nội dung và tạo HTML tương ứng
        let contentHTML = "";

        // Nếu là ảnh
        if (content.includes('http') && /\.(jpg|jpeg|png|gif|webp)$/i.test(content)) {
            contentHTML = `<img src="${content}" class="img-fluid rounded" style="max-width: 100%; max-height: 300px;">`;
        }
        // Nếu là file có phần mở rộng
        else if (content.includes('http') && /\.(docx?|xlsx?|pptx?|pdf|zip|rar|cpp|txt)$/i.test(content)) {
            const filename = decodeURIComponent(content.split('/').pop());
            const fileExtension = filename.split('.').pop().toLowerCase();

            // Chọn icon phù hợp với loại file
            let fileIcon = 'fa-file';
            if (['doc', 'docx'].includes(fileExtension)) fileIcon = 'fa-file-word';
            else if (['xls', 'xlsx'].includes(fileExtension)) fileIcon = 'fa-file-excel';
            else if (['ppt', 'pptx'].includes(fileExtension)) fileIcon = 'fa-file-powerpoint';
            else if (fileExtension === 'pdf') fileIcon = 'fa-file-pdf';
            else if (['zip', 'rar'].includes(fileExtension)) fileIcon = 'fa-file-archive';
            else if (['cpp', 'txt', 'js', 'html', 'css'].includes(fileExtension)) fileIcon = 'fa-file-code';

            contentHTML = `
                <a href="${content}" target="_blank" class="d-flex align-items-center text-reset text-decoration-none">
                    <i class="fas ${fileIcon} fa-2x me-2"></i>
                    <span class="${isOwnMessage ? 'text-white' : ''}">${filename}</span>
                </a>
            `;
        }
        // Nếu là text
        else {
            contentHTML = `<p class="mb-0">${content}</p>`;
        }

        // Tạo HTML cho tin nhắn theo kiểu Messenger
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

    // Auto resize textarea khi nhập nội dung dài
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';

        // Giới hạn chiều cao tối đa
        const maxHeight = 150;
        if (this.scrollHeight > maxHeight) {
            this.style.height = maxHeight + 'px';
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }
    });

    // Cuộn xuống cuối khi trang được tải
    chatBox.scrollTop = chatBox.scrollHeight;
});