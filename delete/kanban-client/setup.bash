#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Gateway Management App (Tailwind v3 + React 18)"

# === Question: reinstall? ===
if [ -f package.json ] && grep -q '"start"' package.json; then
  echo
  read -p "Found package.json. Reinstall dependencies? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting without reinstall..."
    npm start
    exit 0
  else
    rm -rf node_modules package-lock.json
  fi
fi

# === INSTALL ONLY STABLE VERSIONS (v3 for Tailwind!) ===
echo "Creating package.json..."
cat > package.json << 'EOF'
{
  "name": "kanban-client",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-scripts": "5.0.1",
    "lucide-react": "^0.380.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.38",
    "autoprefixer": "^10.4.19"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": ["react-app", "react-app/jest"]
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }
}
EOF

echo "Installing dependencies..."
npm install

# === Tailwind config (only if not exists) ===
if [ ! -f tailwind.config.js ]; then
  echo "Generating tailwind.config.js..."
  npx tailwindcss init -p
fi

# === Check postcss.config.js ===
if [ ! -f postcss.config.js ]; then
  echo "Generating postcss.config.js..."
  cat > postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF
fi

# === Optional: fix ESLint warnings in App.jsx ===
# Remove unused imports and add handleMouseMove to useEffect dependencies
APP_FILE="src/components/App.jsx"
if [ -f "$APP_FILE" ]; then
  echo "Optimizing App.jsx (removing unused imports and fixing useEffect)..."
  # Remove Edit3 and ArrowRight from imports
  sed -i "s/ Edit3,//" "$APP_FILE"
  sed -i "s/ ArrowRight,//" "$APP_FILE"
  # Fix useEffect - add handleMouseMove to dependencies
  sed -i '/useEffect(() => {/,/}, \[draggedElement, dragOffset\]);/c\
  useEffect(() => {\
    if (draggedElement) {\
      document.addEventListener("mousemove", handleMouseMove);\
      document.addEventListener("mouseup", stopDrag);\
      return () => {\
        document.removeEventListener("mousemove", handleMouseMove);\
        document.removeEventListener("mouseup", stopDrag);\
      };\
    }\
  }, [draggedElement, dragOffset, handleMouseMove]);\
' "$APP_FILE"
fi

echo
echo "Done! Starting the application..."
npm start