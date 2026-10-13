#![cfg_attr(windows, windows_subsystem = "windows")]
use anyhow::{Context, Result, ensure};
use craftapps_portable_updater::*;
use std::{fs, path::PathBuf, process::Command};

fn run() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    ensure!(
        args.next().as_deref() == Some(std::ffi::OsStr::new("--root")),
        "Missing root argument"
    );
    let root = PathBuf::from(args.next().context("Missing root path")?).canonicalize()?;
    let args: Vec<_> = args.collect();
    if args.first().is_some_and(|a| a == "--check-update") {
        if let Err(e) = update(&root) {
            log(
                &root,
                &format!("Update failed; current version retained: {e:#}"),
            );
            return Err(e);
        }
        return Ok(());
    }
    if args.first().is_some_and(|a| a == "--rollback") {
        use fs2::FileExt;
        let lock = fs::OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(root.join("update.lock"))?;
        lock.try_lock_exclusive()
            .context("An update is running; retry later")?;
        let mut state = read_state(&root)?;
        let previous = state.previous.take().context("No previous version")?;
        read_build(&root.join("versions").join(&previous))?;
        state.previous = Some(state.current);
        state.current = previous;
        atomic_json(&root.join("state.json"), &state)?;
        fs::write(
            root.join("updates-paused.txt"),
            "Remove this file to resume updates after rollback.\n",
        )?;
        log(&root, "Rolled back; automatic updates paused");
        return Ok(());
    }
    let state = read_state(&root)?;
    let dir = root.join("versions").join(state.current);
    let build = read_build(&dir)?;
    let data = root.join("data");
    fs::create_dir_all(&data)?;
    let _probe = tempfile::NamedTempFile::new_in(&data)?;
    let mut app = Command::new(dir.join(relative(&build.executable)?));
    app.current_dir(&root)
        .args(&args)
        .env("PHOTOCRAFT_CONFIG_DIR", &data)
        .env("PDFCRAFT_CONFIG_DIR", &data);
    // The applications are native GUI binaries. No shell and no terminal is launched.
    app.stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()?;
    if !root.join("updates-paused.txt").exists() {
        let mut check = Command::new(std::env::current_exe()?);
        hidden(&mut check)
            .arg("--root")
            .arg(&root)
            .arg("--check-update")
            .spawn()?;
    }
    log(
        &root,
        &format!(
            "Launched {} {} ({})",
            build.app, build.version, build.upstream
        ),
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        if let Ok(root) = find_root() {
            log(&root, &format!("Runtime error: {e:#}"));
        }
        std::process::exit(1);
    }
}
