# view contents of rpm file: rpm -qlp <filename>.rpm

%define         _contrailopt /opt/contrail
%if 0%{?_buildTag:1}
%define         _relstr      %{_buildTag}
%else
%define         _relstr      %(date -u +%y%m%d%H%M)
%endif
%{echo: "Building release %{_relstr}\n"}
%if 0%{?_srcVer:1}
%define         _verstr      %{_srcVer}
%else
%define         _verstr      1
%endif


Name:		    contrail-fabric-utils
Version:	    %{_verstr}
Release:	    %{_relstr}
Summary:	    Contrail Fabric Utilities%{?_gitVer}
BuildArch:          noarch

Group:		    Applications/System
License:	    Commercial

Source0:            git_root

%description
Contrail Fabric Utilities for cluster management

BuildRequires:  systemd-units

%prep
if [ ! -d contrail-fabric-utils]; then
    git clone ssh://git@bitbucket.org/contrail_admin/fabric-utils.git contrail-fabric-utils
else
    (cd contrail-fabric-utils; git pull)
fi


%build
rm -rf contrail-fabric-utils/contrail_fabric_utils-0.1dev
rm -rf contrail-fabric-utils/contrail_fabric_utils.egg-info
(cd contrail-fabric-utils; %{__python} setup.py sdist)

%clean

%install
rm -rf %{buildroot}
install -d -m 755 %{buildroot}%{python_sitelib}
install -d -m 755 %{buildroot}%{_contrailopt}/utils

pushd contrail-fabric-utils
tar zxf dist/contrail_fabric_utils-0.1dev.tar.gz
cd contrail_fabric_utils-0.1dev
%{__python} setup.py install --root=%{buildroot}
cp README %{buildroot}%{_contrailopt}/utils/README.fabric
cp -R %{buildroot}%{python_sitelib}/contrail_fabric_utils/fabfile %{buildroot}%{_contrailopt}/utils/fabfile
popd

%post

%files
%defattr(-, root, root)
%{python_sitelib}/contrail_fabric_utils
%{python_sitelib}/contrail_fabric_utils-*.egg-info
%{_contrailopt}/utils/README.fabric
%{_contrailopt}/utils/fabfile


%changelog

