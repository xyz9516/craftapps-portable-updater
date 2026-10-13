use anyhow::{Context, Result, bail, ensure};
use ed25519_dalek::{Signature, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::Duration,
};

pub const REPOSITORY: &str = "xyz9516/craftapps-portable-updater";
pub const PUBLIC_KEY: &str = include_str!("../release-public-key.txt");
pub const SCHEMA: u32 = 1;
pub const MAX_ARCHIVE: u64 = 1024 * 1024 * 1024;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Build {
    pub schema: u32,
    pub version: String,
    pub app: String,
    pub platform: String,
    pub upstream: String,
    pub updater_commit: String,
    pub patch_sha256: String,
    pub executable: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct State {
    pub schema: u32,
    pub current: String,
    pub previous: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Asset {
    pub app: String,
    pub platform: String,
    pub url: String,
    pub sha256: String,
    pub size: u64,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Channel {
    pub schema: u32,
    pub version: String,
    pub assets: Vec<Asset>,
}

pub fn component(value: &str) -> Result<()> {
    ensure!(
        !value.is_empty() && value.len() < 160,
        "Invalid identifier length"
    );
    ensure!(
        value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'.'),
        "Invalid identifier"
    );
    ensure!(value != "." && value != "..", "Invalid identifier");
    Ok(())
}

pub fn relative(value: &str) -> Result<PathBuf> {
    ensure!(
        !value.contains('\\') && !value.contains(':'),
        "Invalid relative path"
    );
    let p = PathBuf::from(value);
    ensure!(
        !p.as_os_str().is_empty()
            && p.components()
                .all(|c| matches!(c, std::path::Component::Normal(_))),
        "Unsafe relative path"
    );
    Ok(p)
}

pub fn atomic_json(path: &Path, value: &impl Serialize) -> Result<()> {
    let parent = path.parent().context("No parent directory")?;
    fs::create_dir_all(parent)?;
    let mut tmp = tempfile::NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(&mut tmp, value)?;
    tmp.write_all(b"\n")?;
    tmp.as_file().sync_all()?;
    tmp.persist(path).map_err(|e| e.error)?;
    Ok(())
}

pub fn read_state(root: &Path) -> Result<State> {
    let state: State = serde_json::from_slice(&fs::read(root.join("state.json"))?)?;
    ensure!(state.schema == SCHEMA, "Unsupported installation schema");
    component(&state.current)?;
    if let Some(p) = &state.previous {
        component(p)?;
    }
    Ok(state)
}

pub fn read_build(dir: &Path) -> Result<Build> {
    let build: Build = serde_json::from_slice(&fs::read(dir.join("build.json"))?)?;
    ensure!(build.schema == SCHEMA, "Unsupported build schema");
    ensure!(
        matches!(build.app.as_str(), "photocraft" | "pdfcraft"),
        "Unknown application"
    );
    ensure!(
        matches!(
            build.platform.as_str(),
            "windows-x64" | "macos-arm64" | "macos-x64"
        ),
        "Unknown platform"
    );
    semver::Version::parse(&build.version)?;
    let exe = relative(&build.executable)?;
    ensure!(
        dir.join(exe).is_file() && dir.join(runtime_name()).is_file(),
        "Incomplete version directory"
    );
    Ok(build)
}

pub fn runtime_name() -> &'static str {
    if cfg!(windows) {
        "craft-runtime.exe"
    } else {
        "craft-runtime"
    }
}

pub fn hidden(command: &mut Command) -> &mut Command {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
}

pub fn log(root: &Path, message: &str) {
    let _ = fs::create_dir_all(root.join("logs"));
    let path = root.join("logs/updater.log");
    if fs::metadata(&path)
        .map(|m| m.len() > 4 * 1024 * 1024)
        .unwrap_or(false)
    {
        let _ = fs::rename(&path, root.join("logs/updater.previous.log"));
    }
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(path) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let _ = writeln!(f, "{now} {message}");
    }
}

pub fn verify_channel(bytes: &[u8], signature: &[u8], key: &str) -> Result<Channel> {
    let key: [u8; 32] = hex::decode(key.trim())?
        .try_into()
        .map_err(|_| anyhow::anyhow!("Invalid public key"))?;
    VerifyingKey::from_bytes(&key)?.verify_strict(bytes, &Signature::from_slice(signature)?)?;
    let channel: Channel = serde_json::from_slice(bytes)?;
    ensure!(channel.schema == SCHEMA, "Unsupported update schema");
    semver::Version::parse(&channel.version)?;
    Ok(channel)
}

pub fn asset_url(url: &str) -> Result<()> {
    let prefix = format!("https://github.com/{REPOSITORY}/releases/download/");
    ensure!(
        url.starts_with(&prefix) && !url.contains(['?', '#', '\\']) && !url.contains("/../"),
        "Update is not a release asset from the configured repository"
    );
    Ok(())
}

fn agent() -> ureq::Agent {
    ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(900)))
        .build()
        .into()
}

pub fn download(url: &str, max: u64, out: &mut impl Write) -> Result<u64> {
    let mut response = agent()
        .get(url)
        .header("User-Agent", "CraftApps-Portable-Updater")
        .call()?;
    let size = std::io::copy(&mut response.body_mut().as_reader().take(max + 1), out)?;
    ensure!(size <= max, "Download exceeds size limit");
    Ok(size)
}

pub fn sha256_file(path: &Path) -> Result<String> {
    let mut f = fs::File::open(path)?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = f.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(hex::encode(hash.finalize()))
}

pub fn extract(archive: &Path, destination: &Path) -> Result<()> {
    let mut zip = zip::ZipArchive::new(fs::File::open(archive)?)?;
    ensure!(zip.len() <= 20000, "Too many archive entries");
    let mut total = 0u64;
    for i in 0..zip.len() {
        let mut entry = zip.by_index(i)?;
        let name = entry.name().trim_end_matches('/');
        let path = destination.join(relative(name)?);
        let mode = entry.unix_mode().unwrap_or(0o644);
        ensure!(
            mode & 0o170000 != 0o120000,
            "Symlinks are not accepted in updates"
        );
        ensure!(entry.size() <= MAX_ARCHIVE, "Archive member too large");
        total = total
            .checked_add(entry.size())
            .context("Archive size overflow")?;
        ensure!(total <= 2 * MAX_ARCHIVE, "Expanded archive too large");
        if entry.is_dir() {
            fs::create_dir_all(&path)?;
            continue;
        }
        fs::create_dir_all(path.parent().context("No parent")?)?;
        let mut out = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let count = std::io::copy(&mut entry, &mut out)?;
        ensure!(count == entry.size(), "Truncated archive entry");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(
                &path,
                fs::Permissions::from_mode(if mode & 0o111 != 0 { 0o755 } else { 0o644 }),
            )?;
        }
    }
    Ok(())
}

pub fn activate(
    root: &Path,
    staged: &Path,
    channel: &Channel,
    asset: &Asset,
    current: &Build,
) -> Result<()> {
    let build = read_build(staged)?;
    ensure!(
        build.app == current.app
            && build.platform == current.platform
            && build.version == channel.version,
        "Payload identity mismatch"
    );
    ensure!(
        asset.app == build.app && asset.platform == build.platform,
        "Asset identity mismatch"
    );
    ensure!(
        semver::Version::parse(&build.version)? > semver::Version::parse(&current.version)?,
        "Refusing downgrade or repeated release"
    );
    let id = format!(
        "{}-{}",
        build.version,
        &asset.sha256.get(..16).context("Invalid checksum")?
    );
    component(&id)?;
    let mut state = read_state(root)?;
    let target = root.join("versions").join(&id);
    // A fresh random staging directory is moved as a whole; existing versions are never overwritten.
    ensure!(
        !target.exists(),
        "Version directory already exists; inspect before retrying"
    );
    fs::rename(staged, &target)?;
    state.previous = Some(state.current);
    state.current = id;
    atomic_json(&root.join("state.json"), &state)?;
    Ok(())
}

pub fn update(root: &Path) -> Result<()> {
    use fs2::FileExt;
    let lock = fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(root.join("update.lock"))?;
    if lock.try_lock_exclusive().is_err() {
        return Ok(());
    }
    let state = read_state(root)?;
    let current = read_build(&root.join("versions").join(state.current))?;
    let base = format!("https://github.com/{REPOSITORY}/releases/latest/download");
    let mut bytes = Vec::new();
    let mut signature = Vec::new();
    download(&format!("{base}/channel.json"), 1024 * 1024, &mut bytes)?;
    download(&format!("{base}/channel.sig"), 64, &mut signature)?;
    let channel = verify_channel(&bytes, &signature, PUBLIC_KEY)?;
    if semver::Version::parse(&channel.version)? <= semver::Version::parse(&current.version)? {
        log(root, "Already up to date");
        return Ok(());
    }
    let matches: Vec<_> = channel
        .assets
        .iter()
        .filter(|a| a.app == current.app && a.platform == current.platform)
        .collect();
    ensure!(matches.len() == 1, "Expected one matching release asset");
    let asset = matches[0];
    asset_url(&asset.url)?;
    ensure!(
        asset.size > 0
            && asset.size <= MAX_ARCHIVE
            && asset.sha256.len() == 64
            && hex::decode(&asset.sha256).is_ok(),
        "Invalid asset metadata"
    );
    let temp = tempfile::tempdir_in(root)?;
    let archive = temp.path().join("update.zip");
    let mut file = fs::File::create(&archive)?;
    ensure!(
        download(&asset.url, asset.size, &mut file)? == asset.size,
        "Asset size mismatch"
    );
    file.sync_all()?;
    drop(file);
    ensure!(
        sha256_file(&archive)? == asset.sha256,
        "Asset checksum mismatch"
    );
    let staged = temp.path().join("payload");
    fs::create_dir(&staged)?;
    extract(&archive, &staged)?;
    activate(root, &staged, &channel, asset, &current)?;
    log(
        root,
        &format!("Version {} is ready for the next launch", channel.version),
    );
    Ok(())
}

pub fn find_root() -> Result<PathBuf> {
    let exe = std::env::current_exe()?;
    for ancestor in exe.ancestors().skip(1).take(7) {
        if ancestor.join("state.json").is_file() {
            return Ok(ancestor.to_path_buf());
        }
    }
    bail!("Portable state.json not found; extract the entire ZIP first")
}

#[cfg(test)]
mod tests;
