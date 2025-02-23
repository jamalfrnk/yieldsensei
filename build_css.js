
const execSync = require('child_process').execSync;
execSync('npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify');
