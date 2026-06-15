import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 100 }, // Ramp-up to 100 users over 30 seconds
        { duration: '1m', target: 1000 }, // Ramp-up to 1000 users and hold for 1 minute
        { duration: '30s', target: 0 },   // Ramp-down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
        ws_connecting: ['p(95)<200'],     // 95% of WebSocket connections must establish below 200ms
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const WS_URL = __ENV.WS_URL || 'ws://localhost:8000/ws';

export default function () {
    // 1. Test API Gateway Health/Auth
    const res = http.get(`${BASE_URL}/health`);
    check(res, { 'status was 200': (r) => r.status == 200 });
    
    // 2. Simulate Student connecting to WebSocket for IDE Execution
    const wsRes = ws.connect(`${WS_URL}/execution`, function (socket) {
        socket.on('open', function () {
            // Send code execution payload
            socket.send(JSON.stringify({
                command: 'execute',
                language: 'python',
                code: 'print("Hello from k6 load test!")',
                userId: `student_${__VU}`
            }));
        });

        socket.on('message', function (msg) {
            let data = JSON.parse(msg);
            check(data, { 'received expected output': (d) => d.output !== undefined });
            socket.close();
        });

        socket.on('error', function (e) {
            if (e.error() != "websocket: close sent") {
                console.log('An unexpected error occurred: ', e.error());
            }
        });

        socket.setTimeout(function () {
            console.log('Timeout, closing connection');
            socket.close();
        }, 10000);
    });

    check(wsRes, { 'websocket connection successful': (r) => r && r.status === 101 });
    sleep(1);
}
