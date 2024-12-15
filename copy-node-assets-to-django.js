const fs = require('fs');
const path = require('path');

// Define the common target directory for all assets
const targetDir = 'workflow/static/external';

const assets = [
  'node_modules/ag-grid-community/dist/ag-grid-community.min.js',
  'node_modules/ag-grid-community/styles/ag-grid.css',
  'node_modules/ag-grid-community/styles/ag-theme-alpine.css',
  'node_modules/jsoneditor/dist/jsoneditor.min.js',
  'node_modules/jsoneditor/dist/jsoneditor.min.css',
  'node_modules/jquery/dist/jquery.min.js',
  'node_modules/highcharts/highcharts.js',
  'node_modules/jspdf/dist/jspdf.umd.min.js',
  'node_modules/jspdf-autotable/dist/jspdf.plugin.autotable.min.js',
  'node_modules/sortablejs/Sortable.min.js',
];

if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

assets.forEach((source) => {
  const fileName = path.basename(source);
  const targetPath = path.join(targetDir, fileName);

  fs.copyFileSync(path.resolve(source), targetPath);
  console.log(`Copied ${source} to ${targetPath}`);
});
console.log('Asset copying completed.');