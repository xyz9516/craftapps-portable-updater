#![cfg_attr(windows, windows_subsystem = "windows")]
use craftapps_portable_updater::*;

fn run() -> anyhow::Result<()> {
    let root = find_root()?;
    let state = read_state(&root)?;
    let version = root.join("versions").join(state.current);
    read_build(&version)?;
    let mut child = std::process::Command::new(version.join(runtime_name()));
    hidden(&mut child)
        .arg("--root")
        .arg(&root)
        .args(std::env::args_os().skip(1))
        .spawn()?;
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        if let Ok(root) = find_root() {
            log(&root, &format!("Launcher failed: {e:#}"));
        }
        std::process::exit(1);
    }
}
