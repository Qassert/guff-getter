"""Best-effort local forward/reverse derivatives of completed videos."""
from fractions import Fraction
import fcntl
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import threading


log = logging.getLogger(__name__)
DERIVATION_VERSION = 1


def valid_mp4(path):
    try:
        with Path(path).open('rb') as stream:
            header = stream.read(12)
        return len(header) == 12 and header[4:8] == b'ftyp'
    except OSError:
        return False


class PingPongVideos:
    def path(self, source):
        source = Path(source)
        return source.with_name(f'{source.stem}-pingpong.mp4')

    def failure_path(self, source):
        return self.path(source).with_suffix('.failed')

    def lock_path(self, source):
        return self.path(source).with_suffix('.lock')

    def available(self, source):
        source, target = Path(source), self.path(source)
        try:
            if valid_mp4(target) and target.stat().st_mtime_ns >= source.stat().st_mtime_ns:
                return target
        except OSError:
            pass
        return None

    def can_attempt(self, source):
        source = Path(source)
        if not valid_mp4(source) or self.available(source):
            return False
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            return False
        failed = self.failure_path(source)
        try:
            if not failed.is_file():
                return True
            marker = json.loads(failed.read_text())
            stat = source.stat()
            return not (marker.get('version') == DERIVATION_VERSION
                        and marker.get('source_mtime_ns') == stat.st_mtime_ns
                        and marker.get('source_size') == stat.st_size)
        except (OSError, ValueError, TypeError, AttributeError):
            # Old/plain or malformed markers predate this implementation version and
            # cannot permanently suppress a corrected local conversion.
            return True

    def failure_reason(self, source):
        try:
            marker = json.loads(self.failure_path(source).read_text())
            return str(marker.get('reason') or 'unknown local FFmpeg failure')[:300]
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def preferred(self, source):
        return self.available(source) or Path(source)

    @staticmethod
    def _frame_count(source, ffprobe):
        result = subprocess.run([
            ffprobe, '-v', 'error', '-count_frames', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_read_frames,r_frame_rate', '-of', 'json', str(source)
        ], capture_output=True, text=True, timeout=60, check=True)
        stream = json.loads(result.stdout)['streams'][0]
        frames = int(stream['nb_read_frames'])
        # Validate the reported frame-rate even though FFmpeg preserves the source timing.
        if Fraction(stream['r_frame_rate']) <= 0:
            raise ValueError('Invalid source frame rate.')
        return frames

    def derive(self, source):
        """Create one atomic local derivative; never invokes a media provider."""
        source = Path(source)
        existing = self.available(source)
        if existing:
            return existing
        if not self.can_attempt(source):
            return None
        target, failed, lock_path = self.path(source), self.failure_path(source), self.lock_path(source)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a+b') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return self.available(source)
            existing = self.available(source)
            if existing:
                return existing
            source_stat = source.stat()
            temporary = target.with_name(
                f'.{target.stem}.{os.getpid()}.{threading.get_ident()}.tmp.mp4')
            try:
                log.info('[pingpong] %s deriving', source.stem)
                ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
                frames = self._frame_count(source, ffprobe)
                if frames < 4:
                    raise ValueError('Source video has too few frames.')
                # The reverse leg omits its first (END) and last (START) frames. This
                # avoids holding either turnaround when the derived file itself loops.
                filters = (f'[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[fwd];'
                           f'[r]reverse,trim=start_frame=1:end_frame={frames - 1},'
                           'setpts=PTS-STARTPTS[rev];'
                           '[fwd][rev]concat=n=2:v=1:a=0[v]')
                subprocess.run([
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                    '-filter_complex', filters, '-map', '[v]', '-an', '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temporary)
                ], capture_output=True, text=True, timeout=300, check=True)
                current = source.stat()
                if (current.st_mtime_ns, current.st_size) != (source_stat.st_mtime_ns, source_stat.st_size):
                    raise RuntimeError('Original video changed during local derivation.')
                if not valid_mp4(temporary):
                    raise RuntimeError('Local ping-pong output is not a valid MP4.')
                os.replace(temporary, target)
                failed.unlink(missing_ok=True)
                log.info('[pingpong] %s derivative ready', source.stem)
                return target
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                try:
                    failed.write_text(json.dumps({
                        'version': DERIVATION_VERSION,
                        'source_mtime_ns': source_stat.st_mtime_ns,
                        'source_size': source_stat.st_size,
                        'reason': type(exc).__name__ + ': ' + str(exc)[:240],
                    }))
                except OSError:
                    pass
                log.warning('[pingpong] %s derivation failed: %s', source.stem, exc)
                return None

    def remove(self, source):
        """Remove only local derivative state associated with an owned original."""
        source = Path(source)
        lock_path = self.lock_path(source)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with lock_path.open('a+b') as lock:
                # Deletion/replacement waits for a bounded FFmpeg process so a late
                # atomic rename cannot recreate an orphan after cleanup.
                fcntl.flock(lock, fcntl.LOCK_EX)
                for path in (self.path(source), self.failure_path(source)):
                    if path.is_file() and not path.is_symlink():
                        path.unlink()
        except OSError:
            pass


service = PingPongVideos()
