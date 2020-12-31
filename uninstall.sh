pip3 uninstall node_configure
git rm -r dist
git rm -r build
git rm -r node_configure.egg-info
rm -r dist
rm -r build
rm -r node_configure.egg-info
git add .
git commit -m "remove old build"

