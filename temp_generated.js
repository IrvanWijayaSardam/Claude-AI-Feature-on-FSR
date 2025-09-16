Java.perform(function() {
    console.log("[+] Frida script started - Hooking sesame function");

    try {
        // Hook the Java getFlag method to see the constructed password
        var FlagstaffHill = Java.use("com.hellocmu.picoctf.FlagstaffHill");

        // Hook getFlag method
        FlagstaffHill.getFlag.implementation = function(input, ctx) {
            console.log("[+] getFlag called with input: " + input);

            // Calculate the correct password based on the Java logic
            var witches = ["weatherwax", "ogg", "garlick", "nitt", "aching", "dismass"];
            var second = 3 - 3;  // 0
            var third = (3 / 3) + second;  // 1
            var fourth = (third + third) - second;  // 2
            var fifth = 3 + fourth;  // 5
            var sixth = (fifth + second) - third;  // 4
            var password = witches[fifth] + "." + witches[third] + "." + witches[second] + "." +
                          witches[sixth] + "." + witches[3] + "." + witches[fourth];

            console.log("[+] ✓ CORRECT INPUT FOR APP: " + password);
            console.log("[+] Password breakdown:");
            console.log("    witches[5] = " + witches[fifth]);  // dismass
            console.log("    witches[1] = " + witches[third]);   // ogg
            console.log("    witches[0] = " + witches[second]);  // weatherwax
            console.log("    witches[4] = " + witches[sixth]);   // aching
            console.log("    witches[3] = " + witches[3]);       // nitt
            console.log("    witches[2] = " + witches[fourth]);  // garlick

            var result = this.getFlag(input, ctx);
            console.log("[+] getFlag result: " + result);
            return result;
        };

        // Hook the native sesame function
        FlagstaffHill.sesame.implementation = function(input) {
            console.log("[+] Java sesame wrapper called with: " + input);
            var result = this.sesame(input);
            console.log("[+] Java sesame wrapper result: " + result);
            return result;
        };

    } catch (e) {
        console.log("[-] Java hooks error: " + e);
    }

    // Hook native functions directly
    try {
        var libhellojni = Module.findBaseAddress("libhellojni.so");
        if (libhellojni) {
            console.log("[+] Found libhellojni.so at: " + libhellojni);

            // Hook the native sesame JNI function
            var sesame_addr = libhellojni.add(0x100c);
            console.log("[+] Hooking Java_com_hellocmu_picoctf_FlagstaffHill_sesame at: " + sesame_addr);

            Interceptor.attach(sesame_addr, {
                onEnter: function(args) {
                    console.log("[+] === NATIVE SESAME FUNCTION CALLED ===");

                    // Read the input string parameter
                    try {
                        var env = args[0];
                        var jstr = args[2];
                        var getString = env.readPointer().add(0x548).readPointer();
                        var str_ptr = new NativeFunction(getString, 'pointer', ['pointer', 'pointer', 'pointer'])(env, jstr, ptr(0));
                        var input_str = str_ptr.readCString();

                        console.log("[+] Native sesame input: " + input_str);
                        console.log("[+] Expected for native validation: dismass.ogg.weatherwax.aching.nitt.garlick");

                        // Store for onLeave
                        this.input = input_str;
                        this.env = env;
                        this.jstr = jstr;
                        this.str_ptr = str_ptr;
                    } catch (e) {
                        console.log("[-] Error reading string parameter: " + e);
                    }
                },
                onLeave: function(retval) {
                    console.log("[+] Native sesame returning jstring: " + retval);

                    // Release string if we got it
                    try {
                        if (this.str_ptr && this.env && this.jstr) {
                            var releaseString = this.env.readPointer().add(0x550).readPointer();
                            new NativeFunction(releaseString, 'void', ['pointer', 'pointer', 'pointer'])(this.env, this.jstr, this.str_ptr);
                        }
                    } catch (e) {
                        console.log("[-] Error releasing string: " + e);
                    }
                }
            });

            // Hook basil function (validation function)
            var basil_addr = libhellojni.add(0x1624);
            console.log("[+] Hooking basil validation at: " + basil_addr);

            Interceptor.attach(basil_addr, {
                onEnter: function(args) {
                    var input = args[0].readCString();
                    console.log("[+] === BASIL VALIDATION ===");
                    console.log("[+] Validating input: " + input);
                    console.log("[+] Expected format: dismass.ogg.weatherwax.aching.nitt.garlick");
                    this.input = input;
                },
                onLeave: function(retval) {
                    var isValid = retval.toInt32() === 1;
                    console.log("[+] Validation result: " + (isValid ? "✓ VALID" : "✗ INVALID"));

                    if (isValid) {
                        console.log("[+] 🎉 CORRECT PASSWORD ENTERED!");
                        console.log("[+] Input '" + this.input + "' passed validation!");
                    } else {
                        console.log("[+] ❌ Wrong password!");
                        console.log("[+] Input: " + this.input);
                        console.log("[+] Try: dismass.ogg.weatherwax.aching.nitt.garlick");
                    }
                }
            });

            // Hook oregano function (flag generation)
            var oregano_addr = libhellojni.add(0x1b28);
            console.log("[+] Hooking oregano flag generation at: " + oregano_addr);

            Interceptor.attach(oregano_addr, {
                onEnter: function(args) {
                    var input = args[0].readCString();
                    console.log("[+] === OREGANO FLAG GENERATION ===");
                    console.log("[+] Generating flag from: " + input);
                    this.input = input;
                },
                onLeave: function(retval) {
                    if (retval && !retval.isNull()) {
                        var flag = retval.readCString();
                        console.log("[+] 🏁 FLAG GENERATED: " + flag);
                    } else {
                        console.log("[+] oregano returned null/empty");
                    }
                }
            });

            // Hook unscramble function to see the flag decryption process
            var unscramble_addr = libhellojni.add(0x1958);
            console.log("[+] Hooking unscramble at: " + unscramble_addr);

            Interceptor.attach(unscramble_addr, {
                onEnter: function(args) {
                    console.log("[+] === UNSCRAMBLE DECRYPTION ===");
                    console.log("[+] param_1 (encrypted data): " + args[0]);
                    console.log("[+] param_2 (data size): " + args[1]);
                    console.log("[+] param_3 (key): " + args[2]);
                    console.log("[+] param_4 (key size): " + args[3]);

                    try {
                        var keyStr = args[2].readCString();
                        console.log("[+] Key string: " + keyStr);
                    } catch (e) {
                        console.log("[+] Could not read key as string");
                    }
                },
                onLeave: function(retval) {
                    if (retval && !retval.isNull()) {
                        console.log("[+] Unscramble returned decrypted data at: " + retval);
                        try {
                            var decrypted = retval.readCString();
                            console.log("[+] 🔓 DECRYPTED FLAG: " + decrypted);
                        } catch (e) {
                            console.log("[+] Could not read decrypted data as string");
                        }
                    }
                }
            });

        } else {
            console.log("[-] Could not find libhellojni.so");
        }
    } catch (e) {
        console.log("[-] Native hooks error: " + e);
    }

    console.log("\n[+] ================================================");
    console.log("[+] 🔑 ANSWER: The correct password to enter is:");
    console.log("[+] dismass.ogg.weatherwax.aching.nitt.garlick");
    console.log("[+] ================================================");
    console.log("[+] Script ready - Click the button in the app!");
});