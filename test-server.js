const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;

const server = http.createServer((req, res) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
    
    if (req.url === '/debug') {
        // Debug endpoint to see what files exist
        const currentDir = __dirname;
        const files = fs.readdirSync(currentDir);
        
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`
            <html>
            <head><title>Debug Info</title></head>
            <body>
                <h1>Debug Information</h1>
                <h2>Current Directory: ${currentDir}</h2>
                <h3>Files in current directory:</h3>
                <ul>
                    ${files.map(f => `<li>${f}</li>`).join('')}
                </ul>
                <h3>africa_monitoring.json exists:</h3>
                <p>${fs.existsSync(path.join(currentDir, 'africa_monitoring.json')) ? 'YES' : 'NO'}</p>
                ${fs.existsSync(path.join(currentDir, 'africa_monitoring.json')) ? 
                    `<h3>File content preview:</h3><pre>${fs.readFileSync(path.join(currentDir, 'africa_monitoring.json'), 'utf-8').substring(0, 500)}...</pre>` 
                    : ''}
            </body>
            </html>
        `);
    } else {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end('<html><body><h1>Test Server Running!</h1><p>Visit <a href="/debug">/debug</a> for debug info</p></body></html>');
    }
});

server.listen(PORT, () => {
    console.log(`Test server running on port ${PORT}`);
    console.log(`Current directory: ${__dirname}`);
});

