// YieldSensei Web App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Handle bot command forms
    document.querySelectorAll('.command-form').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const command = form.dataset.command;
            const input = form.querySelector('input').value;

            try {
                const response = await fetch(`/api/${command}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ token: input })
                });

                const data = await response.json();
                showNotification(data.message);
            } catch (error) {
                console.error('Error:', error);
                showNotification('Failed to process command. Please try again.', 'error');
            }
        });
    });

    // Notification handler
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Handle info tooltips
    const infoTooltips = document.querySelectorAll('.info-tooltip');
    infoTooltips.forEach(tooltip => {
        const button = tooltip.querySelector('.info-icon');
        if (button) {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                tooltip.classList.toggle('active');
            });
        }
    });

    // Close tooltips when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.info-tooltip')) {
            infoTooltips.forEach(tooltip => {
                tooltip.classList.remove('active');
            });
        }
    });
});
