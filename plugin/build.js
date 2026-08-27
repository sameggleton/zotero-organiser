import esbuild from 'esbuild';
import fs from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';

const isWatch = process.argv.includes('--watch');
const isPackage = process.argv.includes('--package');

const outDir = path.resolve('build');
const distDir = path.resolve('dist');

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy icon asset
const chromeIconsDir = path.resolve('chrome/content/icons');
fs.mkdirSync(chromeIconsDir, { recursive: true });
const svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="#7c3aed">
  <path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42zM5.5 7C4.67 7 4 6.33 4 5.5S4.67 4 5.5 4 7 4.67 7 5.5 6.33 7 5.5 7z"/>
</svg>`;
fs.writeFileSync(path.join(chromeIconsDir, 'tag-purple.svg'), svgIcon);

const buildOptions = {
  entryPoints: ['src/index.ts'],
  bundle: true,
  outfile: 'build/addon.js',
  target: ['firefox115', 'es2022'],
  format: 'iife',
  globalName: 'ZoteroOrganiserModule',
  sourcemap: 'inline',
  platform: 'browser',
  define: {
    'process.env.NODE_ENV': '"production"',
  },
};

async function run() {
  if (isWatch) {
    const ctx = await esbuild.context(buildOptions);
    await ctx.watch();
    console.log('⚡ Watching for changes...');
  } else {
    await esbuild.build(buildOptions);
    console.log('✅ Build completed: build/addon.js');

    if (isPackage) {
      console.log('📦 Packaging .xpi...');
      const zip = new AdmZip();
      zip.addLocalFile(path.resolve('manifest.json'));
      zip.addLocalFile(path.resolve('bootstrap.js'));
      const licensePath = fs.existsSync(path.resolve('LICENSE'))
        ? path.resolve('LICENSE')
        : fs.existsSync(path.resolve('../LICENSE'))
        ? path.resolve('../LICENSE')
        : null;
      if (licensePath) {
        zip.addLocalFile(licensePath);
      }
      zip.addLocalFolder(path.resolve('build'), 'build');
      zip.addLocalFolder(path.resolve('chrome'), 'chrome');
      if (fs.existsSync(path.resolve('locale'))) {
        zip.addLocalFolder(path.resolve('locale'), 'locale');
      }

      const xpiPath = path.join(distDir, 'zotero-organiser.xpi');
      zip.writeZip(xpiPath);
      console.log(`🎉 Packaged plugin successfully: ${xpiPath}`);
    }
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
