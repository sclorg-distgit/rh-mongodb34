# Define SCL name
%{!?scl_name_prefix: %global scl_name_prefix rh-}
%{!?scl_name_base: %global scl_name_base mongodb}
%{!?version_major: %global version_major 3}
%{!?version_minor: %global version_minor 4}
%{!?scl_name_version: %global scl_name_version %{version_major}%{version_minor}}
%{!?scl: %global scl %{scl_name_prefix}%{scl_name_base}%{scl_name_version}}

# Turn on new layout -- prefix for packages and location
# for config and variable files
# This must be before calling %%scl_package
%{!?nfsmountable: %global nfsmountable 1}

# Define SCL macros
%{?scl_package:%scl_package %scl}

# do not produce empty debuginfo package (https://bugzilla.redhat.com/show_bug.cgi?id=1061439#c2)
%global debug_package %{nil}

# Convert SCL name into uppercase including - to _ conversion
%if 0%{?scl:1}
%global scl_upper %{lua:print(string.upper(string.gsub(rpm.expand("%{scl}"), "-", "_")))}
%endif


Summary:	Package that installs %{scl}
Name:		%{scl}
Version:	3.0
Release:	11%{?dist}
License:	GPLv2+
Group:		Applications/File
# template of man page with RPM macros to be expanded
Source0:	README
# mongodb license
Source1:	LICENSE
Requires:       %{name}-runtime = %{version}
Requires:	scl-utils
Requires:	%{?scl_prefix}mongodb-server
BuildRequires:	scl-utils-build, help2man
%if 0%{?rhel} >= 7
BuildRequires:	rh-maven35-scldevel
BuildRequires:	rh-maven35-javapackages-local
%endif

%description
This is the main package for %{scl} Software Collection, which installs
necessary packages to use MongoDB %{version_major}.%{version_minor} server.
Software Collections allow to install more versions of the same package
by using alternative directory structure.
Install this package if you want to use MongoDB %{version_major}.%{version_minor}
server on your system

%package runtime
Summary:	Package that handles %{scl} Software Collection.
Group:		Applications/File
Requires:	scl-utils
Requires(post):	policycoreutils-python, libselinux-utils

%description runtime
Package shipping essential scripts to work with %{scl} Software Collection.

%package build
Summary:	Package shipping basic build configuration
Requires:	scl-utils-build
Requires:	scl-utils-build-helpers
Requires:	%{name}-scldevel = %{version}
%if 0%{?rhel} >= 7
Requires:	rh-maven35-scldevel
%endif
Group:		Applications/File

%description build
Package shipping essential configuration macros to build
%scl Software Collection.

%package scldevel
Summary:	Package shipping development files for %{scl}.
Group:		Applications/File
Requires:       %{name}-runtime = %{version}

%description scldevel
Development files for %{scl} (useful e.g. for hierarchical collection
building with transitive dependencies).

%prep
%setup -c -T

# This section generates README file from a template and creates man page
# from that file, expanding RPM macros in the template file.
cat <<'EOF' | tee README
%{expand:%(cat %{SOURCE0})}
EOF

# copy the license file so %%files section sees it
cp %{SOURCE1} .

%build
# temporary helper script used by help2man
cat <<\EOF | tee h2m_helper
#!/bin/sh
if [ "$1" = "--version" ]; then
  printf '%%s' "%{?scl_name} %{version} Software Collection"
else
  cat README
fi
EOF
chmod a+x h2m_helper
# generate the man page
help2man -N --section 7 ./h2m_helper -o %{?scl_name}.7
sed -i "s|'|\\\\N'39'|g" %{?scl_name}.7

%install
%{?scl_install}
%{?scl_install_java}

# create enable scriptlet that sets correct environment for collection
cat << EOF | tee -a %{buildroot}%{?_scl_scripts}/enable
# For binaries
export PATH="%{_bindir}:%{_sbindir}\${PATH:+:\${PATH}}"
# For header files
export CPATH="%{_includedir}\${CPATH:+:\${CPATH}}"
# For libraries during build
export LIBRARY_PATH="%{_libdir}\${LIBRARY_PATH:+:\${LIBRARY_PATH}}"
# For libraries during linking
export LD_LIBRARY_PATH="%{_libdir}\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}"
# For man pages; empty field makes man to consider also standard path
export MANPATH="%{_mandir}:\${MANPATH:-}"
# For Java Packages Tools to locate java.conf
export JAVACONFDIRS="%{_sysconfdir}/java\${JAVACONFDIRS:+:}\${JAVACONFDIRS:-}"
# For XMvn to locate its configuration file(s)
export XDG_CONFIG_DIRS="%{_sysconfdir}/xdg:\${XDG_CONFIG_DIRS:-/etc/xdg}"
# For systemtap
export XDG_DATA_DIRS="%{_datadir}:\${XDG_DATA_DIRS:-/usr/local/share:%{_mandir}}"
# For pkg-config
export PKG_CONFIG_PATH="%{_libdir}/pkgconfig\${PKG_CONFIG_PATH:+:\${PKG_CONFIG_PATH}}"
# For Java RPM generators
export PYTHONPATH="%{_scl_root}%{python_sitearch}:%{_scl_root}%{python_sitelib}\${PYTHONPATH:+:}\${PYTHONPATH:-}"
# For golang packages in collection (for building mongo tools)
export GOPATH="%{_datadir}/gocode\${GOPATH:+:\${GOPATH}}"
EOF

# generate service-environment file for mongo[ds] configuration
cat >> %{buildroot}%{_scl_scripts}/service-environment << EOF
# Services are started in a fresh environment without any influence of user's
# environment (like environment variable values). As a consequence,
# information of all enabled collections will be lost during service start up.
# If user needs to run a service under any software collection enabled, this
# collection has to be written into %{scl_upper}_SCLS_ENABLED variable in
# /opt/rh/sclname/service-environment.
%{scl_upper}_SCLS_ENABLED='%{scl}'
EOF

# install generated man page
install -d -m 755               %{buildroot}%{_mandir}/man7
install -p -m 644 %{?scl_name}.7 %{buildroot}%{_mandir}/man7/

# create directory for license
install -d -m 755 %{buildroot}%{_licensedir}

# create directory not create by scl_install
install -d -m 755 %{buildroot}%{_datadir}/gocode
install -d -m 755 %{buildroot}%{_datadir}/gocode/src
install -d -m 755 %{buildroot}%{_libdir}/cmake
install -d -m 755 %{buildroot}%{_libdir}/pkgconfig

# generate rpm macros file for depended collections
cat << EOF | tee -a %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel
%%scl_%{scl_name_base} %{?scl}
%%scl_prefix_%{scl_name_base} %{?scl_prefix}
EOF


%post runtime
# Simple copy of context from system root to SCL root.
# In case new version needs some additional rules or context definition,
# it needs to be solved by changing selinux-policy.
semanage fcontext -a -e / %{?_scl_root} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_sysconfdir} %{_sysconfdir} >/dev/null 2>&1 || :
semanage fcontext -a -e %{_root_localstatedir} %{_localstatedir} >/dev/null 2>&1 || :
selinuxenabled && load_policy || :
restorecon -R %{?_scl_root} >/dev/null 2>&1 || :
restorecon -R %{_sysconfdir} >/dev/null 2>&1 || :
restorecon -R %{_localstatedir} >/dev/null 2>&1 || :

#define license tag if not already defined (RHEL6)
%{!?_licensedir:%global license %doc}

%files

%if 0%{?rhel} >= 7 || 0%{?fedora} >= 15
%{?scl_install_java:%files runtime -f filesystem -f .java-filelist}
%{!?scl_install_java:%files runtime -f filesystem}
%dir %attr(0755, root, root) %{_licensedir}/
%else
%files runtime
%endif
%license LICENSE
%doc README
%{?scl_files}
%config(noreplace) %{_scl_scripts}/service-environment
%{_mandir}/man7/%{?scl_name}.*
# Directories for golang code (requrements of mongo-tools)
%dir %{_datadir}/gocode
%dir %{_datadir}/gocode/src


%files build
%license LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl}-config

%files scldevel
%license LICENSE
%{_root_sysconfdir}/rpm/macros.%{scl_name_base}-scldevel

%changelog
* Mon Aug 07 2017 Marek Skalický <mskalick@redhat.com> - 3.0-11
- Add back missing rh-maven35-javapackages-local needed for scl_install_java

* Fri Jul 21 2017 Marek Skalický <mskalick@redhat.com> - 3.0-10
- Remove rh-maven35 dependency

* Mon Jun 26 2017 Marek Skalický <mskalick@redhat.com> - 3.0-9
- Add missing directory ownership

* Mon Jun 26 2017 Marek Skalický <mskalick@redhat.com> - 3.0-8
- Install javapackages-local for building

* Mon Jun 26 2017 Marek Skalický <mskalick@redhat.com> - 3.0-7
- Use license directive on RHEL6 too

* Fri Jun 23 2017 Michael Simacek <msimacek@redhat.com> - 3.0-6
- Update for rh-maven35 and scl_install_java

* Fri Jun 23 2017 Marek Skalický <mskalick@redhat.com> - 3.0-5
- Use rh-maven35 on RHEL7
- Set GOPATH to be able to use mongo-tools sources in user project build

* Fri Jun 23 2017 Marek Skalický <mskalick@redhat.com> - 3.0-4
- Add scl-utils-build-helpers build dependency

* Tue Jun 20 2017 Marek Skalický <mskalick@redhat.com> - 3.0-3
- Add java configuration back

* Thu Jun 8 2017 Marek Skalicky <mskalick@redhat.com> - 3.0-2
- Remove odd chars from enable script

* Mon Jun 5 2017 Marek Skalicky <mskalick@redhat.com> - 3.0-1
- Initial commit (converted rh-mongodb32.spec)
- Use recommended softwarecollection.org way to redefine env variables in enable script

