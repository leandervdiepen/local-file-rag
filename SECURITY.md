# Security

This app reads the files on your disk and builds an index of what is in them.
If you find a way to get any of that off the machine, please tell me before you tell anyone else.

## Reporting

Open a [private security advisory](https://github.com/leandervdiepen/local-file-rag/security/advisories/new),
or email leander.vandiepen@chaptr.com.

Please include what you did, what you expected, and what happened instead.
A failing script is worth more than a description.
I will confirm within a few days and tell you plainly whether I think it is a real issue.

There is no bounty. This is one person's project.

## What counts

The load-bearing claim is that **your files, the index, the page images and every embedding stay on this machine**, and that exactly three things reach the network:

1. The retrieval model downloads once from Hugging Face, 4.43 GB, on the first search or crawl that needs it.
2. Opening a provider in settings asks that provider what models it has and what they cost. It sends your key and nothing else.
3. Asking a question sends the five matched page images to the provider you picked. Choosing Ollama keeps this one on the machine too.

Anything that breaks that is the most serious kind of bug here:

- A fourth outbound call, of any kind, from either process.
- A page image, an embedding, a filename or a snippet of file text reaching a host other than the provider the user picked for that one question.
- A provider key written to disk by the sidecar, into a log, into an error message, or into a crash report. The sidecar holds keys in memory only (D41); the Electron side keeps them in the OS keychain through `safeStorage`.
- Reaching the local HTTP API without the bearer token, from another process, another user on the machine, or a web page in a browser.
- Getting the app to index or read a file outside the folders the user added.
- Anything that survives quitting the app and keeps reading the disk.

## What does not

- **Anything that needs to already be running as you.** The sidecar binds 127.0.0.1 on a port the OS assigns and requires a bearer token generated per launch. Another user on the machine cannot reach it. You, with a debugger, can reach everything, and that is true of every app you own.
- **The index being readable on disk.** It is in your own Application Support directory with your own permissions. Encrypting it against yourself would buy nothing and cost the search.
- **The model download not being pinned to a hash.** It is the Hugging Face client fetching a named revision from `huggingface.co`, the same as every other project on the machine. `HF_HUB_OFFLINE=1` stops it reaching out at all once the cache is warm.
- **A provider seeing the pages you sent it.** That is what asking the question does. The app tells you which five pages it is about to send, and the whole feature is optional.
- **The app being unsigned.** It is not notarised with an Apple Developer ID, which is why macOS quarantines it and the README tells you to clear the flag. That is a distribution gap, not a vulnerability, and the DMG's SHA-256 is on the release.

## Supported versions

The latest release. There is no back-porting.
