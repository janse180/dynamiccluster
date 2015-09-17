Name: dynamiccluster
Version: 0.5.0
Release: %{?buildid}%{?dist}
Summary: A cluster in the cloud solution
Group:   System Environment/Daemons
License: ASL 2.0
URL:     http://github.com/eResearchSA/dynamiccluster

Source0: %{name}-%{version}.tar.gz
Source1: initd-script
Source2: dynamiccluster.yaml

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

Requires: python-pip
Requires: PyYAML
Requires: python-jinja2
Requires: python-requests

%description
Dynamic Cluster can dynamically launch and destroy worker nodes in OpenStack or AWS for Torque or SGE according to workload.

%prep

%setup
%{__cat} <<EOF >sysconfig-dynamiccluster
ROOT_DIR="/usr/share/dynamiccluster"
EOF

%build

%install
%{__rm} -rf %{buildroot}
%{__mkdir_p} %{buildroot}%{_localstatedir}/lib/%{name}
%{__install} -Dp -m0755 %{SOURCE1} %{buildroot}%{_initrddir}/dynamiccluster
%{__install} -d -m 0700 %{buildroot}%{_sysconfdir}/dynamiccluster/
%{__install} -Dp -m0600 %{SOURCE2} %{buildroot}%{_sysconfdir}/dynamiccluster/
%{__install} -Dp -m0644 sysconfig-dynamiccluster %{buildroot}%{_sysconfdir}/sysconfig/dynamiccluster
%{__install} -d %{buildroot}%{_var}/run/dynamiccluster
%{__install} -d %{buildroot}%{_datadir}/dynamiccluster/
%{__cp} -r $RPM_BUILD_DIR/%{name}-%{version}/dynamiccluster* %{buildroot}%{_datadir}/dynamiccluster/
%{__cp} -r $RPM_BUILD_DIR/%{name}-%{version}/html %{buildroot}%{_datadir}/dynamiccluster/
%{__cp} -r $RPM_BUILD_DIR/%{name}-%{version}/scripts %{buildroot}%{_datadir}/dynamiccluster/

%clean
%{__rm} -rf %{buildroot}

%post
if [ $1 -eq 1 ]; then
    /sbin/chkconfig --add dynamiccluster
fi
echo "If you want to use OpenStack as your cloud resoource, please install python-novaclient."
echo "    e.g. pip install python-novaclient"
echo "If you want to use AWS as your cloud resoource, please install boto."
echo "    e.g. pip install boto (You may need to install gcc-c++ and python-devel with yum before installing boto)"

%preun
if [ $1 -eq 0 ]; then
    /sbin/service dynamiccluster stop >/dev/null 2>&1 || :
    /sbin/chkconfig --del dynamiccluster
fi

%postun

%files
%defattr(-, root, root, 0755)
%doc LICENSE
%config(noreplace) %{_sysconfdir}/sysconfig/dynamiccluster
%config(noreplace) %{_sysconfdir}/dynamiccluster/
%attr(0755, root, root) %{_initrddir}/dynamiccluster
%{_datadir}/dynamiccluster/
%dir %{_var}/run/dynamiccluster

%changelog
* Mon Oct 17 2015 Shunde Zhang <shunde.zhang@ersa.edu.au> - 0.5.0
- First release.

