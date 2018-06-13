# =========================================================================
#
#   gui2tcl generated test
#
#   Script use parameters in 'config.tcl' placed in current dir.
#
# =========================================================================

# -------------------------------------------------------------------------
# global vars:
#

# directory of this script
set ScriptDirName [file dirname [file normalize [info script]]]

# -------------------------------------------------------------------------
# Initialization of user preferences
#

set bEnableLogging 0; # Enable (1) to create TclAPI log file

set bEnableStopStatusMsgs 0; # Enable (1) to stop run-time status messages

# -------------------------------------------------------------------------
# prepare test (import project-test) and return test handle
#

proc prepareTest {} {
    global ScriptDirName
    cd $ScriptDirName
    source config.tcl
    return [prepareTestFromConfig Config]
}

proc prepareTestFromConfig {config} {

    # --- access to assoc. array of config params --------
    
    upvar 1 $config Config

    # --- change current dir to script directory ---------
    
    global ScriptDirName
    cd $ScriptDirName

    # --- import project test ----------------------------
    
    if {$Config(IsCompact) == 0} {
        if {[catch {
            if {![catch {av::handleOfName system1 projects $Config(ProjectName)} projectHandle]} {
                av::dputs STATUS -nonewline "Removing the old project, $Config(ProjectName)..."
                av::delete $projectHandle
                av::dputs STATUS " - done"
            }
            set projectHandle [av::perform CreateProject system1 -name $Config(ProjectName) -version $Config(ProjectVersion)]
            set testHandle [av::create test -under $projectHandle -name $Config(TestName) -testType $Config(TestType)]
            configTest $projectHandle $testHandle
            av::perform Save $projectHandle
        } errorText ]} {
            return -code error $errorText
        }
    } else {
        set SpfFileName [file normalize $Config(TestFile)]
        av::dputs STATUS -nonewline "Import project and test from '$SpfFileName' ..."
        set projectHandles [av::perform import system1 -spfFile $SpfFileName]
        av::dputs STATUS " - done"

        # Take care of the case where there may
        # be more than one project in the spf file.
        # We need to find the handle of the project
        # specified in the configuration file.
        set noOfProjects [llength $projectHandles]
        if {$noOfProjects > 0} {
            set foundProjectHandle 0
            foreach projectHandle $projectHandles {
                if {[regexp "${Config(ProjectName)}*" [av::get $projectHandle -name]]} {
                    set foundProjectHandle 1
                    break
                }
            }
            if {!$foundProjectHandle} {
                return -code error "Project, \"$Config(ProjectName)\", specified in configuration file is not found in $SpfFileName"
            }
        } else {
            return -code error "No projects found in $SpfFileName"
        }

        # --- get imported test handle ---
        set testHandles [av::get $projectHandle -tests]
        set noOfTests [llength $testHandles]
        # Take care of the case where there may be more
        # than one test in the project, spf file brings.
        # We need to find the handle of the test specified
        # in the configuration file.
        if {$noOfTests > 0} {
            set foundTestHandle 0
            foreach testHandle $testHandles {
                if {$Config(TestName) == [av::get $testHandle -name]} {
                    set foundTestHandle 1
                    break
                }
            }
            if {!$foundTestHandle} {
                return -code error "Test, \"$Config(TestName)\", specified in configuration file is not found in $SpfFileName"
            }
        } else {
            return -code error "No tests found in $SpfFileName"
        }
    }

    return $testHandle
}

# -------------------------------------------------------------------------

proc runTest {} {
    global env
    global auto_path
    global AV_PORT
    global ScriptDirName
    global bEnableLogging
    global bEnableStopStatusMsgs

    # port map for addr -> handle
    array set PortHandles {}

    if {[catch {
        
        # --- change current dir to script directory --
        
        cd $ScriptDirName

        # --- read and adjust config ------------------
        
        source config.tcl

        if {$Config(IsPortable)} {
            if {! [info exists env(SPIRENT_TCLAPI_ROOT)]} {
                return -code error "Portable mode defined, but\
                    SPIRENT_TCLAPI_ROOT environment variable is not defined"
            }
            set Config(TclAPIRoot) $env(SPIRENT_TCLAPI_ROOT)
        
            if {! [info exists env(SPIRENT_TCLAPI_LICENSEROOT)]} {
                return -code error "Portable mode defined, but\
                                    SPIRENT_TCLAPI_LICENSEROOT environment\
                                    variable is not defined"
            }
            set Config(TclAPILicenseRoot) $env(SPIRENT_TCLAPI_LICENSEROOT)
        } else {
            set Config(TclAPIRoot) [file normalize $Config(TclAPIRoot)]
            set Config(TclAPILicenseRoot) "$Config(TclAPIRoot)/../license"
        }

        if {$Config(OutputDir) == ""} {
            # relative to the current dir (script directory):
            set Config(OutputDir) {.}
        }
        set Config(OutputDir) [file normalize $Config(OutputDir)]
        if {! [info exists Config(AvPort)]} {
            # default xmlrpc port for avalanche:
            set Config(AvPort) 9195
        }        
        if {! [info exists Config(TrialIfNoLicense)]} {
            # default behaviour if no license found - run as trial
            set Config(TrialIfNoLicense) 1
        }       
        if {! [info exists Config(SetProfileForce)]} {
            set Config(SetProfileForce) 0
        }
        
        # --- import packages -------------------------
        
        lappend auto_path $Config(TclAPIRoot)
        set AV_PORT $Config(AvPort)
        package forget av
        package require av
        set av::spiGlobals(ScriptDirectory) $ScriptDirName

        if {$bEnableLogging} {
            av::DebugLogFile on
        }

        if {$bEnableStopStatusMsgs} {
            av::StopStatusMsg on
        }

        av::dputs STATUS "Avalanche initialization is complete"
        av::dputs STATUS "Tcl API root: '$Config(TclAPIRoot)'"

        # --- login -----------------------------------

        if {$Config(Username) != ""} {
            av::dputs STATUS -nonewline "Login as '$Config(Username)' ..."
        } else {
            av::dputs STATUS -nonewline "Login as default user ..."
        }
        set SessionId [av::login $Config(Username) -temp-workspace]
        av::dputs STATUS " - done"

	# --- connect -----------------------------
        
        set ports {}
        array set PortModes {}
        array set DeviceIps {}
        foreach port $Config(Ports) {
            # '{port mode}' ==> port mode
            # 'port'        ==> port ""
            foreach {port mode} $port {}

            lappend ports $port
            set PortModes($port) $mode
            
            # collect device's ip
            array set a [parseLocation $port]

            set ip $a(ip)
            set DeviceIps($ip) $ip
        }

        # connect to devices
        foreach ip [lsort -uniq [array names DeviceIps]] {
            av::dputs STATUS -nonewline "Connect to '$ip' ..."
    
            set physChassisHandle [av::connect $ip]
            
            set physChassisTypesArr($ip)\
                              [av::get $physChassisHandle -deviceType]
            
            av::dputs STATUS " - done"
        }
                
        # --- license -----------------------------
        
        set licenseName $Config(License)
        if {!$Config(Trial)} {
            if {$licenseName != ""} {
                av::dputs STATUS -nonewline "Using license '$licenseName' ..."
                set licenseManager [av::get system1 -licensemanager]
                set licenseHandle {}
            
                # --- find license handle of 'licenseName' ---
                foreach handle [av::get $licenseManager -licenses] {
                    if {[av::get $handle -name] == $licenseName} {
                        set licenseHandle $handle
                        break
                    }
                }
            
                if {$licenseHandle == ""} {
                    av::dputs STATUS "\nLicense file '$licenseName'\
                                      has not been yet added as a\
                                      license for TclAPI package"
                    set userProvidedLicensePaths [glob -nocomplain -directory\
                                    $Config(TclAPILicenseRoot) $licenseName*]
                    set foundLicense 0
                    foreach userProvidedLicensePath $userProvidedLicensePaths {
                        set userProvidedLicense [file tail\
                               [file rootname $userProvidedLicensePath]]
                        if {$userProvidedLicense == $licenseName} {
                            set foundLicense 1
                            break
                        }
                    }
                    if {$foundLicense} {
                        av::dputs STATUS -nonewline "Adding license\
                                                    '$licenseName' now..."
                        set licenseHandle [av::create licenses -under\
                                    $licenseManager -name $licenseName\
                                    -file $userProvidedLicensePath]
                        av::config $licenseManager -currentlicense\
                                                    $licenseHandle
                        av::dputs STATUS " - done"
                    } elseif {$Config(TrialIfNoLicense)} {
                        av::dputs WARNING "License '$licenseName' couldn't\
                                     be found. Test will run in TRIAL mode"
                        set Config(Trial) 1
                    } else {
                        av::dputs ERROR "Couldn't locate the license file\
                                         '$licenseName'"
                        return -code error "Either provide the license\
                                file or if you'd like to run in 'TRIAL'\
                                mode, turn it on in the 'config.tcl' file"
                    }
                } else {
                    av::config $licenseManager -currentlicense\
                                                $licenseHandle
                    av::dputs STATUS " - done"
                }
            } else {
                # Just check the first platform if it is STC. Since we
                # don't mix Appliance and STC platforms in a test, it is
                # OK to check only the first instance.
                set deviceType $physChassisTypesArr([lindex [array names\
                                                  physChassisTypesArr] 0])
                if {$deviceType != "STC"} {
                    if {$Config(TrialIfNoLicense)} {
                        av::dputs STATUS "No license is defined. Test\
                                      will be started in TRIAL mode"
                        set Config(Trial) 1
                    } else {
                        av::dputs ERROR "No license file is defined and\
                                    'TRIAL' mode is not turned on\
                                     in the config.tcl file"
                        return -code error "Please either provide a license\
                                        file or turn on the 'TRIAL' mode"
                    }
                }
                # If it is STC chassis, we do nothing...
            }
        } else {
            av::dputs STATUS "Test will be started in TRIAL mode"
        }
        

        # --- reserve ports -----------------------
        
        foreach port $ports {
            av::dputs STATUS -nonewline "Reserve port '$port' ..."
            set flagForce $Config(ReserveForce)
            if {$flagForce} {
                set handle [av::perform ReservePort system1 -port $port -force force]
            } else {
                set handle [av::reserve $port]
            }
            av::dputs STATUS " - done"
            set PortHandles($port) $handle
        }
		
        # --- toggle profiles ---------------------
		
        if {[info exists Config(Profiles)]} {		
            foreach {ip profiles} $Config(Profiles) {
                puts "Toggle profile '$profiles' for device '$ip'"
                
                set deviceHandle [av::connect $ip]
                set forceProfile $Config(SetProfileForce)                
                
                if {$forceProfile} {
                    set setProfileResult [av::waitEvent "set_slot_profile" [av::perform setSlotProfile $deviceHandle -profiles "$profiles" -force force]]
                } else {
                    set setProfileResult [av::waitEvent "set_slot_profile" [av::perform setSlotProfile $deviceHandle -profiles "$profiles"]]
                }
                
                set serverAnswer [lindex $setProfileResult 1]
                
                if {[string equal "Reboot required" $serverAnswer] == 1 && $forceProfile != 1} {
                    return -code error "Test configuration requires profile change, which may take several minutes. If required, please set the 'SetProfileForce' flag in 'config.tcl' file to '1' and re-start the test"
                } elseif {[string equal "Success" $serverAnswer] == 1} {
                    puts "Profile changed successfully"
                    # At this point, av::connect to the chassis is required
                    # to refresh and get the latest port core information
                    set deviceHandle [av::connect $ip]
                } else {
                    return -code error "Profile change failed"
                }
            }
        }
    
        # --- toggle mode -------------------------
        
        foreach port $ports {
            set mode $PortModes($port)

            set handle $PortHandles($port)
            
            set modes [split [av::get $handle -supportedModes] ,]
            if {$mode != "" && $modes != ""} {
                if {[lsearch $modes $mode] != -1} {
                    av::dputs STATUS -nonewline "Toggle mode '$mode' for port '$port' ..."
                    av::config $handle -mode $mode
                    av::dputs STATUS " - done"
                } else {
                    return -code error \
                        "Port '$port' does not support mode '$mode'"
                }
            }
        }
        
        # --- prepare test --------------------
    
        av::dputs STATUS "Preparing test..."
        set TestHandle [prepareTestFromConfig Config]

        set testName [av::get $TestHandle -name]
        set ProjectHandle [av::get $TestHandle -parent]
        set projectName [av::get $ProjectHandle -name]

        # --- configure threatex --------------

        av::dputs STATUS -nonewline "Configuring ThreatEx ..."
        set SaveThreatExPath [av::get system1.serverconfiguration -ThreatPath]
        av::config system1.serverconfiguration -ThreatPath [normalizePath {data/threatex}]
        av::dputs STATUS " - done"

        # --- start test ----------------------
        
        set trial                       $Config(Trial)
        set continueIfAlreadyRunning    1
        set removeOldTest               1
    
        if {$trial} {
            set testMode "TRIAL"
        } else {
            set testMode "Full"
        }
        av::dputs STATUS -nonewline "Run test '$testName' in project '$projectName' in $testMode mode..."
        set RequestId [av::apply\
            $TestHandle $trial $continueIfAlreadyRunning $removeOldTest]
        # no wait RequestId performed
        av::dputs STATUS " - done"
    
        # --- subscribe to RTS ---
    
        set rti [av::get system1 -runningtestinfo]
    
        set rdsClient [av::subscribe client {sum,http,* timeRemaining}]
        set rdoClient [av::get $rdsClient -resultdataobjects]
        set rdsServer [av::subscribe server {sum,tcpConn* tcpConn,*}]
        set rdoServer [av::get $rdsServer -resultdataobjects]
    
        array set lastInfoClient {}
        array set lastInfoServer {}
        set lastStatusMessage ""
    
        # --- main loop ---
    
        set PAUSE 1000
        while {1} {
            after $PAUSE
            
            array set infoTest [ list\
                statusMessage [av::get $rti -statusMessage]\
                runningTestStatus [av::get $rti -runningTestStatus]\
                testStageLabelClient [av::get $rti -testStageLabelClient] ]
    
            # --- status ---
            if {$infoTest(statusMessage) != $lastStatusMessage && \
                $infoTest(statusMessage) != ""} {
                av::dputs STATUS "$infoTest(statusMessage)"
            }
            
            if {$infoTest(runningTestStatus) == "TEST_RUNNING"} {
                array unset infoClient                    
                array set infoClient [ list\
                   timeElapsed [av::get $rdoClient -timeElapsed]\
                   timeRemaining [av::get $rdoClient -timeRemaining]\
                   sum,http,attemptedTxns [av::get $rdoClient -sum,http,attemptedTxns]\
                   sum,http,successfulTxns [av::get $rdoClient -sum,http,successfulTxns]\
                   sum,http,unsuccessfulTxns [av::get $rdoClient -sum,http,unsuccessfulTxns]\
                   sum,http,abortedTxns [av::get $rdoClient -sum,http,abortedTxns] ]
                array unset infoServer
                array set infoServer [ list\
                   timeElapsed [av::get $rdoServer -timeElapsed]\
                   tcpConn,connsPerSec [av::get $rdoServer -tcpConn,connsPerSec]\
                   sum,tcpConn,openConns [av::get $rdoServer -sum,tcpConn,openConns]\
                   sum,tcpConn,closedWithError [av::get $rdoServer -sum,tcpConn,closedWithError]\
                   sum,tcpConn,closedWithNoError [av::get $rdoServer -sum,tcpConn,closedWithNoError]\
                   sum,tcpConn,closedWithReset [av::get $rdoServer -sum,tcpConn,closedWithReset] ]
                    
                # --- client stats: ---

                if {! [arrayEquals infoClient lastInfoClient] && \
                    $infoClient(timeElapsed) != ""} {
                    av::dputs STATUS -nonewline "\nCLIENT:"
                    if {$infoTest(testStageLabelClient) != ""} {
                        av::dputs STATUS -nonewline " $infoTest(testStageLabelClient)"
                    }
                    av::dputs STATUS "\n    Attempted    : $infoClient(sum,http,attemptedTxns)"
                    av::dputs STATUS "    Successful   : $infoClient(sum,http,successfulTxns)"
                    av::dputs STATUS "    Unsuccessful : $infoClient(sum,http,unsuccessfulTxns)"
                    av::dputs STATUS "    Aborted      : $infoClient(sum,http,abortedTxns)"
                    av::dputs STATUS "      TIME (seconds) Elapsed   : $infoClient(timeElapsed)"
                    av::dputs STATUS "      TIME (seconds) Remaining : $infoClient(timeRemaining)"
                }
    
                # --- server stats: ---
                
                if {! [arrayEquals infoServer lastInfoServer] && \
                    $infoServer(timeElapsed) != ""} {
                    av::dputs STATUS -nonewline "\nSERVER:"
                    if {$infoTest(testStageLabelClient) != ""} {
                        av::dputs STATUS -nonewline " $infoTest(testStageLabelClient)"
                    }
                    av::dputs STATUS "\n    Per second        : $infoServer(tcpConn,connsPerSec)"
                    av::dputs STATUS "    Open              : $infoServer(sum,tcpConn,openConns)"
                    av::dputs STATUS "    Closed with error : $infoServer(sum,tcpConn,closedWithError)"
                    av::dputs STATUS "    Closed with reset : $infoServer(sum,tcpConn,closedWithReset)"
                    av::dputs STATUS "    Closed no error   : $infoServer(sum,tcpConn,closedWithNoError)"
                    av::dputs STATUS "      TIME (seconds) Elapsed   : $infoServer(timeElapsed)"
                }
                
            }

            # --- log errors from getEvent --------

            if {[catch {            
                foreach event [av::getEvents] {
                    set event [join $event]
                    set eventMessage [valueByKey $event message]
                    if {$eventMessage == ""} {
                        # name = async_method_completed
                        foreach {eventKey eventValue} [
                                join [valueByKey $event additional]] {
                            if {$eventKey == "error"} {
                                set eventMessage [valueByKey [
                                    join [join $eventValue]
                                    ] message] 
                                break
                            }
                        }
                    }
                    if {$eventMessage != ""} {
                        set eventName [valueByKey $event name]
                        set eventIsInteractive [
                            string match -nocase interactive.* $eventName
                        ]
                        if {! $eventIsInteractive || $Config(ShowInteractive)} {
                            av::dputs STATUS "$eventMessage"
                        }
                    }
                }
            } errorText]} {
                    av::dputs ERROR "$errorText"
            }
            
            # --- done if test completed
            
            if {$infoTest(runningTestStatus) == "TEST_COMPLETED"} {
                break
            }
                
            array set lastInfoClient [array get infoClient]
            array set lastInfoServer [array get infoServer]
            set lastStatusMessage $infoTest(statusMessage)
        }
    
        # --- copy results --------------------
    
        set OutputDir [file join $Config(OutputDir) results]
        file mkdir $OutputDir
        
        set lastTestInfo [av::get system1 -lastfinishedtestinfo]
        set resultsDir [av::get $lastTestInfo -testResultsDir]
        
        if {$resultsDir != ""} {
            av::dputs STATUS -nonewline "Copy results from '$resultsDir' to '$OutputDir' ..."
            file delete -force -- $OutputDir
            file copy -force -- $resultsDir $OutputDir
            av::dputs STATUS " - done"
        }

    } errorText]} {
        lassign $::errorCode class name msg
        if {$class eq "POSIX" && $name eq "SIG" && $msg eq "SIGINT"} {
            av::dputs STATUS "\n--------- Interrupt signal --------------------"
            puts "Test will be ABORTED!"
            # Abort if the test is runnning
            if {$infoTest(runningTestStatus) != "TEST_COMPLETED"} {
                av::perform stop system1 -workspace [av::get system1 -workspace] -force force
            }
        } else {
            av::dputs STATUS "\n--------- error --------------------"
            av::dputs ERROR "$errorText"
        }
    }

    # --- restore ThreatEx ----------------
        
    if {[catch {
        if {[info exists SaveThreatExPath]} {
            av::config system1.serverconfiguration -ThreatPath $SaveThreatExPath
        }
    } errorText]} {
        av::dputs ERROR "$errorText"
    }

    
    # --- release ports -------------------
        
    if {[catch {
        # release only reserved ports (from PortHandles map)
        foreach port [array names PortHandles] {
            av::dputs STATUS -nonewline "Releasing port '$port' ..."
            set handle [av::release $port]
            av::dputs STATUS " - done"
        }
    } errorText]} {
        av::dputs ERROR "$errorText"
    }

    # --- unsubscribe from RTS ---

    if {[catch {
        if {[info exists rdsClient]} {
            av::unsubscribe $rdsClient
        }
        if {[info exists rdsServer]} {
            av::unsubscribe $rdsServer
        }
    } errorText]} {
        av::dputs ERROR "$errorText"
    }
    
    # --- delete project test -------------

    if {[catch {    
        if {[info exists TestHandle]} {
            set keep $Config(KeepTest)
            if {$keep} {
                av::dputs STATUS "Test '$testName' in project '$projectName' is kept"
            } else {
                av::dputs STATUS -nonewline "Deleting test '$testName' ..."
                av::delete $TestHandle
                av::dputs STATUS " - done"
            
                av::dputs STATUS -nonewline "Deleting project '$projectName' ..."
                av::delete $ProjectHandle
                av::dputs STATUS " - done"
            }
        }
    } errorText]} {
        av::dputs ERROR "$errorText"
    }
    
    # --- logout ------------------------------

    if {[catch {
        if {[info exists SessionId]} {
            av::dputs STATUS -nonewline "Logout ..."
            av::logout shutdown     ;# 'shutdown' - terminate ABL
            av::dputs STATUS " - done"
        }
    } errorText]} {
        av::dputs ERROR "$errorText"
    }
}

# -------------------------------------------------------------------------

# check if 'av' package is loaded:
if {[lsearch [package names] av] == -1} {

    if {[catch  {package require Tclx} errr]} {
        puts "\nError adding Tclx package.\n"
        return -code error "$errr"
    }

    signal error sigint

    if {[catch runTest e]} {
        puts "\n--------- ERROR --------------------"
        puts "$e"
    }
    
} else {
    set av::spiGlobals(ScriptDirectory) $ScriptDirName
    av::dputs STATUS "test.tcl loaded"
}
