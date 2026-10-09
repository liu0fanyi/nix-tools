"""Pure runtime environment adaptation; return secrets unchanged, never log values."""
from native_pc_config import translate_path


def adapt_environment(source, *, role, state_root, models, whisper_package):
    if role not in ('private', 'readonly'):
        raise ValueError('Unknown NUC instance role')
    if not all(isinstance(k,str) and isinstance(v,str) for k,v in source.items()):
        raise ValueError('Environment must contain string pairs')
    result = dict(source)
    if role == 'private':
        cli = result.get('DUFS_WHISPER_CLI','whisper-cli')
        if cli not in ('whisper-cli','/usr/local/bin/whisper-cli'):
            raise ValueError('Custom Whisper executable needs explicit compatibility review')
        result['DUFS_WHISPER_CLI'] = whisper_package + '/bin/whisper-cli'
        model = result.get('DUFS_WHISPER_MODEL','/models/ggml-small-q5_1.bin')
        result['DUFS_WHISPER_MODEL'] = translate_path(model, {'/models':models,models:models})
        if result.get('HOME', '/root') not in ('/root', '/home/liou'):
            raise ValueError('Custom Git home needs explicit compatibility review')
        result['HOME'] = state_root + '/private/git-home'
    else:
        # Original read-only instance has no model or dedicated writing key mounts.
        if any(k in result for k in ('HOME','GIT_SSH_COMMAND','GIT_SSH')):
            raise ValueError('Read-only environment must not select writing credentials')
    if any(k in result for k in ('GIT_SSH_COMMAND','GIT_SSH')):
        raise ValueError('Custom Git executable needs explicit compatibility review')
    if any(k.startswith('TAG_NATIVE_') for k in result):
        raise ValueError('Source environment must not override pinned native selections')
    return result
