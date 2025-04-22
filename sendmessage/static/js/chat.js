document.addEventListener("DOMContentLoaded", function () {
    const socket = io();

    const chatBox = document.getElementById("chat-box");
    const form = document.getElementById("chat-form");
    const textarea = form.querySelector("textarea");
    const fileInput = form.querySelector('input[name="file"]');

    const conversationId = chatBox.dataset.conversationId;
    const senderId = parseInt(chatBox.dataset.senderId);
    const partnerName = chatBox.dataset.partnerName || "Đối phương";

    socket.emit('join', { room: conversationId });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const content = textarea.value.trim();
        const file = fileInput.files[0];

        if (!content && !file) return;

        // Gửi file nếu có
        if (file) {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            const fileUrl = data.url;

            socket.emit("send_message", {
                content: fileUrl,
                sender_id: senderId,
                conversation_id: conversationId
            });

            fileInput.value = "";
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

    function appendMessage(content, sender_id, senderName, isOwnMessage) {
        let inner = "";

        // Nếu là ảnh
        if (content.includes('http') && /\.(jpg|jpeg|png|gif|webp)$/i.test(content)) {
            inner = `<img src="${content}" class="img-fluid rounded mt-2" style="max-height: 300px;">`;
        }
        // Nếu là file và có phần mở rộng như .doc, .cpp, .pdf
        else if (content.includes('http') && /\.(docx?|cpp|pdf)$/i.test(content)) {
            const filename = decodeURIComponent(content.split('/').pop());
            // Hiển thị tên file và cho phép tải hoặc mở file
            inner = `
                <a href="${content}" target="_blank" download>
                    ${filename}
                </a>
            `;
        }
        // Nếu là text
        else {
            inner = `<p class="mb-1">${content}</p>`;
        }

        const msgHtml = `
            <div class="mb-3 ${isOwnMessage ? 'text-end' : ''}">
                <p class="mb-1"><strong>${senderName}</strong></p>
                <div class="p-2 rounded ${isOwnMessage ? 'bg-primary text-white' : 'bg-light'}">
                    ${inner}
                </div>
                <small class="text-muted">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>
            </div>
        `;

        chatBox.insertAdjacentHTML("beforeend", msgHtml);
        requestAnimationFrame(() => {
            chatBox.scrollTop = chatBox.scrollHeight;
        });
    }
});
