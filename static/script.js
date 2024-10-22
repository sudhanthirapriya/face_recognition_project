document.getElementById('registrationForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = '<div class="alert alert-info">Processing...</div>';

    const formData = new FormData(document.getElementById('registrationForm'));
    fetch('/register', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        messageDiv.innerHTML = `<div class="alert alert-${data.status}">${data.message}</div>`;
        if (data.status === 'success') {
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        messageDiv.innerHTML = '<div class="alert alert-danger">An error occurred.</div>';
    });
});