const express = require('express');
const app = express();
app.use(express.json());

// Login - hardcoded per test
app.post('/api/auth/login', (req, res) => {
  const { username, password } = req.body;
  if (username === 'admin' && password === 'admin123') {
    res.json({ token: 'test-token-123', user: { username: 'admin' } });
  } else {
    res.status(401).json({ error: 'Credenziali non valide' });
  }
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server on ${PORT}`));
