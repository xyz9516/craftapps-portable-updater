use super::*;
use ed25519_dalek::{Signer, SigningKey};

fn fixture(dir: &Path, version: &str, app: &str) -> Build {
    fs::create_dir_all(dir).unwrap();
    let exe = if cfg!(windows) { "app.exe" } else { "app" };
    fs::write(dir.join(exe), b"test application").unwrap();
    fs::write(dir.join(runtime_name()), b"test updater").unwrap();
    let build = Build {
        schema: SCHEMA,
        version: version.into(),
        app: app.into(),
        platform: "windows-x64".into(),
        upstream: "a".repeat(40),
        updater_commit: "b".repeat(40),
        patch_sha256: "c".repeat(64),
        executable: exe.into(),
    };
    atomic_json(&dir.join("build.json"), &build).unwrap();
    build
}

#[test]
fn signature_rejects_tampered_content_and_wrong_key() {
    let key = SigningKey::from_bytes(&[7; 32]);
    let bytes = br#"{"schema":1,"version":"0.1.0","assets":[]}"#;
    let signature = key.sign(bytes).to_bytes();
    let public = hex::encode(key.verifying_key().as_bytes());
    assert!(verify_channel(bytes, &signature, &public).is_ok());
    let mut altered = bytes.to_vec();
    altered[25] ^= 1;
    assert!(verify_channel(&altered, &signature, &public).is_err());
    assert!(
        verify_channel(
            bytes,
            &signature,
            &hex::encode(SigningKey::from_bytes(&[8; 32]).verifying_key().as_bytes())
        )
        .is_err()
    );
    assert!(verify_channel(bytes, &[0; 64], &public).is_err());
}

#[test]
fn rejects_paths_and_untrusted_download_sources() {
    for bad in [
        "../escape",
        "/absolute",
        "C:/absolute",
        "a/../../b",
        "a\\b",
        "a:stream",
    ] {
        assert!(relative(bad).is_err(), "{bad}");
    }
    for bad in [
        "https://example.com/update.zip",
        "http://github.com/xyz9516/craftapps-portable-updater/releases/download/v1/a.zip",
        "https://github.com/attacker/repo/releases/download/v1/a.zip",
    ] {
        assert!(asset_url(bad).is_err());
    }
    assert!(
        asset_url(
            "https://github.com/xyz9516/craftapps-portable-updater/releases/download/v1/a.zip"
        )
        .is_ok()
    );
}

#[test]
fn activation_updates_runtime_but_preserves_data_and_old_build() {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path().join("portable folder 中文");
    let old = fixture(&root.join("versions/old"), "0.1.0", "pdfcraft");
    fs::create_dir_all(root.join("data")).unwrap();
    fs::write(root.join("data/settings"), "keep me").unwrap();
    atomic_json(
        &root.join("state.json"),
        &State {
            schema: 1,
            current: "old".into(),
            previous: None,
        },
    )
    .unwrap();
    let staged = root.join("staged");
    fixture(&staged, "0.2.0", "pdfcraft");
    fs::write(staged.join(runtime_name()), "new updater patch").unwrap();
    let channel = Channel {
        schema: 1,
        version: "0.2.0".into(),
        assets: vec![],
    };
    let asset = Asset {
        app: "pdfcraft".into(),
        platform: old.platform.clone(),
        url: String::new(),
        sha256: "d".repeat(64),
        size: 1,
    };
    activate(&root, &staged, &channel, &asset, &old).unwrap();
    let state = read_state(&root).unwrap();
    assert_eq!(state.previous.as_deref(), Some("old"));
    assert_eq!(
        fs::read_to_string(
            root.join("versions")
                .join(state.current)
                .join(runtime_name())
        )
        .unwrap(),
        "new updater patch"
    );
    assert_eq!(
        fs::read_to_string(root.join("data/settings")).unwrap(),
        "keep me"
    );
    assert!(root.join("versions/old").is_dir());
}

#[test]
fn invalid_update_never_changes_current_pointer() {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path();
    let old = fixture(&root.join("versions/old"), "0.2.0", "pdfcraft");
    atomic_json(
        &root.join("state.json"),
        &State {
            schema: 1,
            current: "old".into(),
            previous: None,
        },
    )
    .unwrap();
    let staged = root.join("staged");
    fixture(&staged, "0.1.0", "pdfcraft");
    let mut channel = Channel {
        schema: 1,
        version: "0.1.0".into(),
        assets: vec![],
    };
    let asset = Asset {
        app: "pdfcraft".into(),
        platform: old.platform.clone(),
        url: String::new(),
        sha256: "d".repeat(64),
        size: 1,
    };
    assert!(activate(root, &staged, &channel, &asset, &old).is_err());
    fixture(&staged, "0.3.0", "photocraft");
    channel.version = "0.3.0".into();
    assert!(activate(root, &staged, &channel, &asset, &old).is_err());
    assert_eq!(read_state(root).unwrap().current, "old");
}

#[test]
fn extraction_rejects_traversal_without_writing_outside_staging() {
    let temp = tempfile::tempdir().unwrap();
    let archive = temp.path().join("bad.zip");
    let mut zip = zip::ZipWriter::new(fs::File::create(&archive).unwrap());
    zip.start_file("../escape.txt", zip::write::SimpleFileOptions::default())
        .unwrap();
    zip.write_all(b"bad").unwrap();
    zip.finish().unwrap();
    assert!(extract(&archive, &temp.path().join("staging")).is_err());
    assert!(!temp.path().join("escape.txt").exists());
}
