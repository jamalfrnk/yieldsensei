const { execSync } = require('child_process');
const path = require('path');

try {
  console.log('Building CSS...');
  execSync(`npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify`, {
    stdio: 'inherit',
    encoding: 'utf-8',
    cwd: __dirname,
    env: {
      ...process.env,
      PATH: `${path.join(__dirname, 'node_modules', '.bin')}:${process.env.PATH}`
    }
  });
  console.log('CSS build completed successfully');
} catch (error) {
  console.error('Failed to build CSS:', error.message);
  process.exit(1);
}