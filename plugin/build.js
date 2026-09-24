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
