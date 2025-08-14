# UCLA-Map-Game

Interactive map game for exploring UCLA's campus.

## Getting Started

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the development server:

   ```bash
   npm run dev
   ```

   This launches a Vite-powered server on <http://localhost:5173>.

3. Open the project in your browser to play the game.

## Regenerating Map Data

The repository includes `build_ucla_geojson.py` to regenerate the campus
GeoJSON data used by the game.

## Permalinks

Selecting a building updates the URL hash with a query string such as
`?id=123&z=17&c=-118.44500,34.06890`. Visiting the app with that hash will
restore the saved view and reselect the building, enabling easy sharing of
locations.

## Tests

No automated test suite is currently defined. Running `npm test` will report
"Error: no test specified".

