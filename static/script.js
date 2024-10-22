document.getElementById('registrationForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const messageDiv = document.getElementById('message');
    messageDiv.innerHTML = '<div class="alert alert-info">Processing...</div>';

    const formData = new FormData(document.getElementById('registrationForm'));
    fetch('/register', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        return response.json().then(data => ({status: response.status, body: data}));
    })
    .then(({status, body}) => {
        let alertClass = 'danger';
        if (body.status === 'success') {
            alertClass = 'success';
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else if (body.status === 'info') {
            alertClass = 'info';
        } else if (body.status === 'warning') {
            alertClass = 'warning';
        }

        messageDiv.innerHTML = `<div class="alert alert-${alertClass}">${body.message}</div>`;
    })
    .catch(error => {
        console.error('Error:', error);
        messageDiv.innerHTML = '<div class="alert alert-danger">An error occurred.</div>';
    });
});