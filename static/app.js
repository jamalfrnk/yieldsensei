<!DOCTYPE html>
<html>
<head>
<title>YieldSensei Web App</title>
<style>
body {
    font-family: sans-serif;
    background-color: #fff; /* White */
    color: #333; /* Dark Grey */
}
.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}
.command-form {
    background-color: #FFA500; /* Orange */
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 10px;
}
.command-form input[type="text"] {
    width: calc(100% - 22px); /* Adjust for padding */
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 3px;
    box-sizing: border-box;
}
.command-form button {
    background-color: #000; /* Black */
    color: #fff;
    padding: 10px 15px;
    border: none;
    border-radius: 3px;
    cursor: pointer;
}
a {
  color: #000; /* Black */
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}

</style>
</head>
<body>
<div class="container">
    <h1>YieldSensei Web App</h1>

    <div class="command-form" data-command="command1">
        <h2>Command 1</h2>
        <form>
            <input type="text" placeholder="Enter token">
            <button type="submit">Submit</button>
        </form>
    </div>

    <div class="command-form" data-command="command2">
        <h2>Command 2</h2>
        <form>
            <input type="text" placeholder="Enter token">
            <button type="submit">Submit</button>
        </form>
    </div>

    <div>
      <h2>Social Media</h2>
      <a href="#">Twitter</a><br>
      <a href="#">Facebook</a><br>
      <a href="#">Instagram</a>
    </div>
</div>


<script>
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
                // Display result in a notification or modal
                alert(data.message);
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to process command. Please try again.');
            }
        });
    });
});
</script>
</body>
</html>