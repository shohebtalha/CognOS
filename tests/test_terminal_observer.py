from cogn_os.plugins.terminal_observer import TerminalTranscriptObserver


def test_terminal_observer_emits_new_transcript_text(tmp_path):
    transcript = tmp_path / "transcript.log"
    transcript.write_text("first line\n", encoding="utf-8")
    observer = TerminalTranscriptObserver(transcript)

    first = observer.poll()
    transcript.write_text("first line\nerror: broken\n", encoding="utf-8")
    second = observer.poll()

    assert first[0].event_type == "terminal_output"
    assert "error: broken" in second[0].payload["text"]
