"""Register the bundled earnings skill beside an installed schwab-table project."""
import argparse
import json
import shutil
from pathlib import Path

NAME='quarterly-earnings-review'


def register(project,target=None,remove=False):
    project=Path(project).resolve()
    target=Path(target) if target else project.parent/NAME
    config=target/'project.json'
    if target.is_symlink():
        if remove:return target
        raise ValueError(f'{target} is an existing symlink; keep it or choose another skills directory')
    if target.exists():
        if not config.is_file():
            if remove:return target
            raise ValueError(f'{target} is not managed by schwab-table; existing skill preserved')
        managed=json.loads(config.read_text(encoding='utf-8'))
        if managed.get('managed_by')!='schwab-table':
            if remove:return target
            raise ValueError(f'{target} belongs to another installation')
        if remove:
            if Path(managed['project']).resolve()==project:shutil.rmtree(target)
            return target
    elif remove:return target
    shutil.copytree(project/'skills'/NAME,target,dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    config.write_text(json.dumps({'managed_by':'schwab-table','project':str(project)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',default=str(Path(__file__).resolve().parent))
    parser.add_argument('--target');parser.add_argument('--remove',action='store_true')
    args=parser.parse_args()
    try:print(register(args.project,args.target,args.remove))
    except (ValueError,OSError) as exc:parser.exit(2,f'error: {exc}\n')


if __name__=='__main__':main()
