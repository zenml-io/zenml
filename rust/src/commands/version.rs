use rand::seq::SliceRandom;
use std::io::{self, IsTerminal, Write};

/// Version embedded at build time from src/zenml/VERSION
const VERSION: &str = env!("ZENML_VERSION");

/// ASCII art banners matching the Python CLI (src/zenml/cli/version.py)
const ASCII_ARTS: [&str; 5] = [
    r#"
       .-') _   ('-.       .-') _  _   .-')
      (  OO) )_(  OO)     ( OO ) )( '.( OO )_
    ,(_)----.(,------.,--./ ,--,'  ,--.   ,--.),--.
    |       | |  .---'|   \ |  |\  |   `.'   | |  |.-')
    '--.   /  |  |    |    \|  | ) |         | |  | OO )
    (_/   /  (|  '--. |  .     |/  |  |'.'|  | |  |`-' |
     /   /___ |  .--' |  |\    |   |  |   |  |(|  '---.'
    |        ||  `---.|  | \   |   |  |   |  | |      |
    `--------'`------'`--'  `--'   `--'   `--' `------'
    "#,
    r#"
      ____..--'     .-''-.   ,---.   .--. ,---.    ,---.   .---.
     |        |   .'_ _   \  |    \  |  | |    \  /    |   | ,_|
     |   .-'  '  / ( ` )   ' |  ,  \ |  | |  ,  \/  ,  | ,-./  )
     |.-'.'   / . (_ o _)  | |  |\_ \|  | |  |\_   /|  | \  '_ '`)
        /   _/  |  (_,_)___| |  _( )_\  | |  _( )_/ |  |  > (_)  )
      .'._( )_  '  \   .---. | (_ o _)  | | (_ o _) |  | (  .  .-'
    .'  (_'o._)  \  `-'    / |  (_,_)\  | |  (_,_)  |  |  `-'`-'|___
    |    (_,_)|   \       /  |  |    |  | |  |      |  |   |        \
    |_________|    `'-..-'   '--'    '--' '--'      '--'   `--------`
    "#,
    r#"
     ________                      __       __  __
    |        \                    |  \     /  \|  \
     \$$$$$$$$  ______   _______  | $$\   /  $$| $$
        /  $$  /      \ |       \ | $$$\ /  $$$| $$
       /  $$  |  $$$$$$\| $$$$$$$\| $$$$\  $$$$| $$
      /  $$   | $$    $$| $$  | $$| $$\$$ $$ $$| $$
     /  $$___ | $$$$$$$$| $$  | $$| $$ \$$$| $$| $$_____
    |  $$    \ \$$     \| $$  | $$| $$  \$ | $$| $$     \
     \$$$$$$$$  \$$$$$$$ \$$   \$$ \$$      \$$ \$$$$$$$$
    "#,
    r#"
        )                    *      (
     ( /(                  (  `     )\ )
     )\())    (            )\))(   (()/(
    ((_)\    ))\    (     ((_)()\   /(_))
     _((_)  /((_)   )\ )  (_()((_) (_))
    |_  /  (_))    _(_/(  |  \/  | | |
     / /   / -_)  | ' \)) | |\/| | | |__
    /___|  \___|  |_||_|  |_|  |_| |____|
    "#,
    r#"
███████ ███████ ███    ██ ███    ███ ██
   ███  ██      ████   ██ ████  ████ ██
  ███   █████   ██ ██  ██ ██ ████ ██ ██
 ███    ██      ██  ██ ██ ██  ██  ██ ██
███████ ███████ ██   ████ ██      ██ ███████
    "#,
];

/// Print Click-style version output: "zenml, version X.Y.Z"
pub fn print_version_flag() -> io::Result<()> {
    // Match Click's version_option format
    writeln!(io::stderr(), "zenml, version {}", VERSION)
}

/// Print the `zenml version` command output with ASCII art banner
pub fn print_version_command() -> io::Result<()> {
    let mut rng = rand::thread_rng();
    let banner = ASCII_ARTS.choose(&mut rng).unwrap_or(&ASCII_ARTS[0]);

    let stderr = io::stderr();
    let mut handle = stderr.lock();

    // Print the ASCII art banner
    writeln!(handle, "{}", banner)?;

    // Print version with bold formatting if terminal supports it
    if io::stderr().is_terminal() {
        // ANSI bold: \x1b[1m ... \x1b[0m
        writeln!(handle, "\x1b[1mversion: {}\x1b[0m", VERSION)
    } else {
        writeln!(handle, "version: {}", VERSION)
    }
}