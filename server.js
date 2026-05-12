require('dotenv').config();

const express = require('express');
const cors = require('cors');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const app = express();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  }
});

app.use(cors({
  origin: [
    'https://familycontrol-frontend-production.up.railway.app',
    'http://localhost:3000'
  ],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());

app.get('/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');

    res.json({
      status: 'ok',
      database: 'connected'
    });
  } catch (error) {
    console.error('DB HEALTH ERROR:', error);

    res.status(500).json({
      status: 'error',
      database: 'disconnected'
    });
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({
        error: 'Username e password obbligatori'
      });
    }

    const result = await pool.query(
      'SELECT id, username, password_hash, email FROM users WHERE username = $1',
      [username]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        error: 'Credenziali non valide'
      });
    }

    const user = result.rows[0];

    const validPassword = await bcrypt.compare(
      password,
      user.password_hash
    );

    if (!validPassword) {
      return res.status(401).json({
        error: 'Credenziali non valide'
      });
    }

    const token = jwt.sign(
      {
        id: user.id,
        username: user.username,
        email: user.email
      },
      process.env.JWT_SECRET,
      {
        expiresIn: '24h'
      }
    );

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email
      }
    });

  } catch (error) {
    console.error('LOGIN ERROR:', error);

    res.status(500).json({
      error: 'Errore server'
    });
  }
});

function verifyToken(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    return res.status(401).json({
      error: 'Token mancante'
    });
  }

  const token = authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({
      error: 'Token non valido'
    });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({
      error: 'Token scaduto o non valido'
    });
  }
}

app.get('/api/devices', verifyToken, async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT id, name, device_type, status, last_seen, user_id
      FROM devices
      WHERE user_id = $1
      ORDER BY id ASC
      `,
      [req.user.id]
    );

    res.json(result.rows);
  } catch (error) {
    console.error('DEVICES ERROR:', error);

    res.status(500).json({
      error: 'Errore recupero dispositivi'
    });
  }
});

app.post('/api/debug/create-user', async (req, res) => {
  try {
    const { username, password, email, secret } = req.body;

    if (secret !== process.env.RESET_SECRET) {
      return res.status(403).json({
        error: 'Forbidden'
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);

    const result = await pool.query(
      `
      INSERT INTO users (username, password_hash, email)
      VALUES ($1, $2, $3)
      RETURNING id, username, email, created_at
      `,
      [username, passwordHash, email]
    );

    res.status(201).json({
      status: 'ok',
      user: result.rows[0]
    });

  } catch (error) {
    console.error('CREATE USER ERROR:', error);

    res.status(500).json({
      error: 'Errore creazione utente'
    });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
});
