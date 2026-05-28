# LightWeight Chat UI

This folder contains the browser chat UI served by:

```bash
lightweight serve --backend python
```

The Python API loads `index.html` from this folder for the `/` route. If this file is not present in a packaged build, the API falls back to its embedded HTML.

