#!/usr/bin/env node
import chokidar from 'chokidar';
import { $ } from 'zx';

const directoryToWatch = process.argv[2];
if (!directoryToWatch) {
	console.error('Please provide a directory to watch as an argument.');
	process.exit(1);
}

async function handleChange(event, path) {
	console.log(`File ${path} has been ${event}`);
	const containerName = 'dreamy_darwin';
	const src = directoryToWatch;
	const target = `/workspaces/ha-core/config/custom_components/inim_cloud/`;
	await $`docker cp ${src}/. ${containerName}:${target}`;

	await $`docker exec -w /workspaces/ha-core ${containerName} pkill -f "python -m homeassistant -c ./config"`.catch(() => {});
	await $`docker exec -d -w /workspaces/ha-core ${containerName} /home/vscode/.local/ha-venv/bin/python -m homeassistant -c ./config`;
	console.log('Home Assistant service restarted.');
}

console.log(`Watching for changes in: ${directoryToWatch}`);
const watcher = chokidar.watch(directoryToWatch, {
	persistent: true,
	ignoreInitial: true,
	ignored: ['**/.*/**', '**/.*', '**/{node_modules,bower_components,vendor}/**'],
});

watcher.on('all', (event, path) => handleChange(event, path));

watcher.on('error', error => console.error(`Watcher error: ${error}`));

console.log('File watcher started. Press Ctrl+C to stop.');
