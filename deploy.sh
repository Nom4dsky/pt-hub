#!/bin/bash
cd ~/Desktop/KRYS\ PT/WEBSITE/pt-hub
xattr -c ~/Downloads/PTHub.html 2>/dev/null
cp ~/Downloads/PTHub.html index.html
xattr -c index.html 2>/dev/null
git add index.html
git commit -m "${1:-Update PT Hub}"
git push
