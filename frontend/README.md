# Atlas Fresh frontend

React and TypeScript dashboard for the Atlas Fresh daily export plan. The UI
loads the canonical plan from the backend through `PlanContext`; views only
format and filter the business results returned by the API.

```bash
npm install
npm run dev
```

Set `VITE_API_BASE_URL` when the API is not running at
`http://localhost:8000`.
