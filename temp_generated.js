Java.perform(function() {
    console.log("[+] Frida script started - Hooking sesame function");

    // Calculate the correct password from the Java logic
    var witches = ["weatherwax", "ogg", "garlick", "nitt", "aching", "dismass"];
    var second = 3 - 3;     // 0
    var third = (3 / 3) + second;   // 1
    var fourth = (third + third) - second;  // 2
    var fifth = 3 + fourth;     // 5
    var sixth = (fifth + second) - third;   // 4

    var correctPassword = witches[fifth] + "." + witches[third] + "." + witches[second] + "." +
                         witches[sixth] + "." + witches[3] + "." + witches[fourth];

    console.log("[+] Calculated correct password: " + correctPassword);

    // Hook the Java sesame method
    try {
        var FlagstaffHill = Java.use("com.hellocmu.picoctf.FlagstaffHill");

        FlagstaffHill.sesame.implementation = function(input) {
            console.log("[+] Java sesame called with parameter: " + input);
            var result = this.sesame(input);
            console.log("[+] Java sesame returned: " + result);
            return result;
        };

        FlagstaffHill.getFlag.implementation = function(input, ctx) {
            console.log("[+] getFlag called with input: " + input);
            console.log("[+] CORRECT KEY NEEDED: " + correctPassword);
            var result = this.getFlag(input, ctx);
            console.log("[+] getFlag returned: " + result);
            return result;
        };

        console.log("[+] Java hooks installed successfully");
    } catch (e) {
        console.log("[!] Error hooking Java methods: " + e);
    }

    // Hook the native sesame function
    try {
        var baseAddr = Module.getBaseAddress("libhellojni.so");
        if (baseAddr) {
            console.log("[+] libhellojni.so base address: " + baseAddr);

            var sesameAddr = baseAddr.add(0x100c);
            console.log("[+] Native sesame function at: " + sesameAddr);

            Interceptor.attach(sesameAddr, {
                onEnter: function(args) {
                    console.log("[+] Native sesame called!");
                    console.log("[+] JNIEnv: " + args[0]);
                    console.log("[+] jobject: " + args[1]);
                    console.log("[+] jstring parameter: " + args[2]);

                    // Extract the string parameter
                    var env = args[0];
                    var jstr = args[2];
                    if (jstr != 0) {
                        var strPtr = env.add(0x548).readPointer().readPointer();
                        var nativeStr = new NativeFunction(strPtr, 'pointer', ['pointer', 'pointer', 'pointer'])(env, jstr, 0);
                        var inputStr = nativeStr.readCString();
                        console.log("[+] Input string: " + inputStr);
                        console.log("[+] CORRECT KEY TO INPUT: " + correctPassword);
                    }
                },
                onLeave: function(retval) {
                    console.log("[+] Native sesame returned: " + retval);
                }
            });

            // Hook the basil validation function
            var basilAddr = baseAddr.add(0x1624);
            console.log("[+] Basil function at: " + basilAddr);

            Interceptor.attach(basilAddr, {
                onEnter: function(args) {
                    console.log("[+] Basil validation called!");
                    if (args[0] != 0) {
                        var inputStr = args[0].readCString();
                        console.log("[+] Validating input: " + inputStr);
                        console.log("[+] Expected format: dismass.ogg.weatherwax.aching.nitt.garlick");
                        console.log("[+] CORRECT KEY: " + correctPassword);
                    }
                },
                onLeave: function(retval) {
                    var isValid = retval.toInt32() == 1;
                    console.log("[+] Validation result: " + (isValid ? "VALID" : "INVALID"));
                    if (!isValid) {
                        console.log("[!] Input was rejected. Use: " + correctPassword);
                    }
                }
            });

            console.log("[+] Native hooks installed successfully");
        } else {
            console.log("[!] Could not find libhellojni.so");
        }
    } catch (e) {
        console.log("[!] Error hooking native functions: " + e);
    }

    console.log("[+] ===== SUMMARY =====");
    console.log("[+] When the button is clicked, input this key: " + correctPassword);
    console.log("[+] This will unlock the sesame function and reveal the flag");
    console.log("[+] Script setup completed");
});