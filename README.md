### About the product
A sleep-tracking web application designed specifically for individuals with irregular sleep schedules. This tool moves away from traditional "calendar-day" tracking, and instead uses a session-based approach to accurately log sleep duration and history.

### Key features
- Uses a "Wake - 1" logic to attribute sleep sessions to the correct "night," regardless of the actual time or day you wake up.
- A "Forgot?" slider allows you to backdate logs by up to 120 minutes if you forget to click the button immediately.
- A "flipped" card view displays precise sleep durations and wake-up times for previous sessions.

### Technical details
About the tech stack
- Frontend: HTML/CSS/JavaScript
- Backend: Python (in folder called "API) using FastAPI
- Database: Neon 
- Deployment: Vercel

What the backend does:
- It queries the database to find the last logged event so the frontend always reflects the user's current status upon loading
- All timestamps are converted to and stored in UTC to ensure mathematical accuracy across different time zones
- It processes the "forgotten minutes" offset by converting the string input to an integer and using Python’s timedelta to subtract time before database insertion

How the frontend calls the backend:
- It uses the JavaScript fetch API
- GET /api/state is called to determine if the UI shouls show the "clocking out" or "Rise & Shine" screen
- POST /api/log is triggered when a button is clicked
- GET /api/history is called when the user clicks "Flip Card" to retrieve the sleep duration info

Where secrets are stored:
- The DATABASE_URL for Neon is stored in a .env file locally and using an environment variable on Vercel