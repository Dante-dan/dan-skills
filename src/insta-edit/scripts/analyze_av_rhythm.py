#!/usr/bin/env python3
"""Local evidence for music/cut rhythm. Not an audio-perception or approval model.

Dependencies: numpy, scipy, librosa, matplotlib; ffmpeg/ffprobe on PATH.
The plan is a JSON with shots[{start,duration,reason?}], matching this video.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


def audio(path, rate, duration=None, offset=0):
    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0",
                                               "-show_entries", "stream=channels", "-of", "json", str(path)]))
    channels = info["streams"][0]["channels"]
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", str(offset), "-i", str(path)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    if channels == 2:
        # Unity average: ffmpeg's default stereo->mono gain may otherwise add 3dB
        # for equal L/R. This still cannot replace per-channel true-peak analysis.
        cmd += ["-af", "pan=mono|c0=0.5*c0+0.5*c1"]
    elif channels != 1:
        raise ValueError("This analyzer supports mono/stereo only; supply a verified downmix")
    cmd += ["-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.check_output(cmd), dtype="<f4").copy()


def rms(y, sr, hop=512, frame=2048):
    values = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop)[0]
    return librosa.frames_to_time(np.arange(len(values)), sr=sr, hop_length=hop), 20 * np.log10(np.maximum(values, 1e-8))


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def nearest(times, t):
    return None if not len(times) else round(float(times[np.argmin(abs(times - t))] - t) * 1000, 1)


def analyze(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(args.plan).read_text())
    duration = float(plan["duration"])
    if not np.isfinite(duration) or duration <= 0 or args.music_offset < 0:
        raise ValueError("Duration must be positive and music offset nonnegative")
    end = 0.
    for shot in plan["shots"]:
        if shot["duration"] <= 0 or abs(shot["start"] - end) > .001:
            raise ValueError("Plan shots must be positive, ordered and contiguous from zero")
        end = shot["start"] + shot["duration"]
    if abs(end - duration) > .001:
        raise ValueError("Plan shot span differs from declared duration")
    video_info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                                      "format=duration", "-of", "json", args.video]))
    if abs(float(video_info["format"]["duration"]) - duration) > .1:
        raise ValueError("Video duration differs from plan; do not map stale cuts")
    sr, hop = 22050, 256
    music = audio(args.music, sr, duration, args.music_offset)
    mixed = audio(args.video, sr, duration)
    if len(music) < sr or len(mixed) < sr:
        raise ValueError("Need at least one second of music and mixed audio")
    if len(music)/sr < duration - .1 or len(mixed)/sr < duration - .1:
        raise ValueError("Music or mixed audio is shorter than timeline")
    onset = librosa.onset.onset_strength(y=music, sr=sr, hop_length=hop)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop, trim=True)
    beats = librosa.frames_to_time(frames, sr=sr, hop_length=hop)
    attacks = librosa.onset.onset_detect(onset_envelope=onset, sr=sr, hop_length=hop, units="time")
    tempo = float(np.asarray(tempo).reshape(-1)[0])
    beat_strength = onset[np.minimum(frames, len(onset) - 1)]
    strong = beats[beat_strength >= np.percentile(beat_strength, 65)] if len(frames) else np.array([])
    # Regularity of a fitted grid is not confidence that the music has that beat.
    mt, mdb = rms(music, sr)
    xt, xdb = rms(mixed, sr)
    cuts = []
    for shot in plan["shots"][1:]:
        t = float(shot["start"])
        cuts.append({"time": t, "reason": shot.get("reason", ""),
                     "nearest_fitted_beat_minus_cut_ms": nearest(beats, t),
                     "nearest_music_attack_minus_cut_ms": nearest(attacks, t),
                     "nearest_strong_candidate_minus_cut_ms": nearest(strong, t)})
    # Visual difference is only an activity proxy; cuts, camera motion and graphics
    # also affect it. Never label it child action or narrative understanding.
    fps, w, h = 12, 96, 54
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-nostdin", "-i", str(args.video),
                                   "-t", str(duration), "-vf", f"fps={fps},scale={w}:{h},format=gray",
                                   "-an", "-f", "rawvideo", "-"])
    pics = np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w).astype(np.float32)
    activity = np.mean(abs(np.diff(pics, axis=0)), axis=(1, 2))
    vt = (np.arange(len(activity)) + 1) / fps
    near_cut = np.zeros(len(vt), dtype=bool)
    for c in cuts:
        near_cut |= abs(vt - c["time"]) < .18
    measured = activity.copy()
    measured[near_cut] = np.nan
    # Oversampling is a screening estimate; AAC true-peak regression remains separate.
    decoded48 = audio(args.video, 48000, duration)
    up = signal.resample_poly(decoded48, 4, 1)
    peak = float(20 * np.log10(max(np.max(abs(up)), 1e-10)))
    windows = []
    for a, b in zip(plan["shots"], plan["shots"][1:]):
        t = float(b["start"])
        windows.append({"time": t, "mix_rms_before_dbfs": round(float(np.mean(xdb[(xt >= t-.2)&(xt < t)])), 2),
                        "mix_rms_after_dbfs": round(float(np.mean(xdb[(xt >= t)&(xt < t+.2)])), 2)})
    report = {"method": "Local librosa music attacks/fitted beat grid + exact plan cuts + decoded mix and visual activity",
              "video": str(Path(args.video).resolve()), "video_sha256": digest(args.video),
              "plan_sha256": digest(args.plan), "music_sha256": digest(args.music),
              "music_offset_seconds": args.music_offset, "duration": duration,
              "estimated_tempo_bpm": round(tempo, 2), "tempo_confidence": "not established by beat tracker alone",
              "beats": beats.round(5).tolist(), "music_attacks": attacks.round(5).tolist(),
              "strong_beat_candidates": strong.round(5).tolist(), "cuts": cuts,
              "cut_mix_energy": windows, "mono_oversampled_peak_dbfs_screen": round(peak, 2),
              "notes": ["Beat alignment is descriptive, not an editing-quality score.",
                        "Music attacks are not phrase boundaries or time-signature proof.",
                        "Band energy and RMS do not identify speech, laughter or their intelligibility.",
                        "Visual difference does not distinguish subject motion, camera movement and graphics.",
                        "No semantic listening, lip sync, emotion, phrase closure or overall approval is claimed."],
              "approval": "analysis_only"}
    if args.original_audio:
        orig = audio(args.original_audio, sr, duration)
        ot, odb = rms(orig, sr)
        report["original_bus_sha256"] = digest(args.original_audio)
        report["original_bus_note"] = "RMS comparison only; music may have ducking and frequencies overlap. Not intelligibility evidence."
    fig, ax = plt.subplots(4, 1, figsize=(15, 10), sharex=True, constrained_layout=True)
    t_on = librosa.times_like(onset, sr=sr, hop_length=hop)
    ax[0].plot(t_on, onset, color="#258294", lw=.8, label="Music attack strength")
    for t in beats: ax[0].axvline(t, color="#cba954", alpha=.2)
    ax[0].set_ylabel("Music attacks")
    ax[0].legend(loc="upper right")
    ax[1].plot(mt, mdb, label="Unmixed music, original level", alpha=.7)
    ax[1].plot(xt, xdb, label="Actual decoded mix", alpha=.85)
    if args.original_audio: ax[1].plot(ot, odb, label="Original-sound bus at edit gain", alpha=.65)
    ax[1].set_ylim(-70, 0); ax[1].set_ylabel("RMS dBFS"); ax[1].legend(loc="upper right")
    ax[2].plot(vt, measured, color="#408861", label="Visual change (cut vicinity excluded)")
    ax[2].set_ylabel("Visual activity"); ax[2].legend(loc="upper right")
    for i, shot in enumerate(plan["shots"]):
        ax[3].barh(0, shot["duration"], left=shot["start"], height=.65, color=plt.cm.Set3(i % 12), edgecolor="white")
        ax[3].text(shot["start"]+shot["duration"]/2, 0, str(i+1), ha="center", va="center")
    ax[3].set_yticks([0], ["Shot #"]);ax[3].set_xlabel("Current timeline seconds")
    for a in ax:
        for c in cuts:a.axvline(c["time"], color="#b84c43", alpha=.65, lw=.8)
        a.set_xlim(0, duration);a.grid(axis="x", alpha=.15)
    fig.suptitle("Audio / video rhythm evidence — analysis only, not listening approval")
    fig.savefig(out/"rhythm-overview.png", dpi=130);plt.close(fig)
    (out/"rhythm.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"output": str(out), "duration": duration, "cuts": len(cuts), "tempo_estimate": tempo}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--music-offset", type=float, default=0)
    ap.add_argument("--original-audio")
    analyze(ap.parse_args())
