# XDCCarr

XDCC Indexer for the *arr ecosystem. Provides a Torznab-compatible API that allows Prowlarr to search XDCC content.

## Features

- Torznab-compatible API
- Searches xdcc.eu for content
- Integrates with Prowlarr as a custom indexer
- Returns results in standard format for Sonarr/Radarr

## Installation

```bash
docker-compose up -d
```

## Prowlarr Configuration

1. Add Indexer → Generic Torznab
2. URL: `http://xdccarr:9117`
3. API Path: `/api`
4. Categories: 2000 (Movies), 5000 (TV)

## API Endpoints

- `GET /` - Status
- `GET /api?t=caps` - Capabilities
- `GET /api?t=search&q=query` - Search
- `GET /api?t=tvsearch&q=show&season=1&ep=1` - TV Search
- `GET /health` - Health check

## License

MIT
