"""Create a local alpha archive; never uploads, publishes or changes visibility."""
import argparse,hashlib,json,shutil,subprocess,tempfile,zipfile
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--publication-approved',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    version={};exec((root/'ue_partyup/__init__.py').read_text(),version)
    label=f"PartyUpPC-{version['__version__']}-alpha-candidate-win64"
    if args.publication_approved: label=label.replace('-alpha-candidate-','-alpha-')
    if not (root/'dist/PartyUpPC/PartyUpPC.exe').is_file():raise SystemExit('Build the standalone bundle first')
    args.output.mkdir(parents=True,exist_ok=True);archive=args.output/(label+'.zip')
    if archive.exists():raise SystemExit('Candidate already exists; choose a new output directory')
    with tempfile.TemporaryDirectory(prefix='partyup-package-') as folder:
        stage=Path(folder)/label;stage.mkdir();shutil.copytree(root/'dist/PartyUpPC',stage/'PartyUpPC')
        for name in ('README.md','LICENSE','PRIVACY.md','THIRD_PARTY_NOTICES.md','Install Private.cmd'):
            shutil.copy2(root/name,stage/name)
        shutil.copytree(root/'licenses',stage/'licenses');shutil.copytree(root/'docs',stage/'docs')
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        (stage/'BUILD-INFO.json').write_text(json.dumps({'version':version['__version__'],'source_commit':commit,'publication':'owner approved public alpha' if args.publication_approved else 'pending owner approval','unsigned':True},indent=2))
        files=sorted(p for p in stage.rglob('*') if p.is_file())
        for p in files:
            parts=[s.lower() for s in p.relative_to(stage).parts]
            if p.suffix.lower() in ('.apk','.pcap','.pcapng','.env') or any(s in ('data','work','.git') or s.startswith(('bugreport','btsnoop')) for s in parts):
                raise SystemExit('Private artifact rejected: '+str(p.relative_to(stage)))
        manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(stage).as_posix()+'\n' for p in files)
        (stage/'SHA256SUMS.txt').write_text(manifest)
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(stage.parent))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest,'files':len(files)+1,'source_commit':commit},indent=2))
if __name__=='__main__':main()
