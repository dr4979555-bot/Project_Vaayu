const {
    app,
    BrowserWindow
} = require("electron");

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const url = require("node:url");


const FRONTEND_ROOT = path.resolve(
    __dirname,
    "..",
    "Frontend"
);

const HOST = "127.0.0.1";
const PORT = 5500;


function getContentType(filePath) {

    const extension =
        path.extname(filePath)
            .toLowerCase();

    const types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav"
    };

    return (
        types[extension] ||
        "application/octet-stream"
    );
}


function startFrontendServer() {

    return new Promise(
        (resolve, reject) => {

            const server =
                http.createServer(
                    (request, response) => {

                        try {

                            const parsedUrl =
                                new url.URL(
                                    request.url,
                                    `http://${HOST}:${PORT}`
                                );

                            let pathname =
                                decodeURIComponent(
                                    parsedUrl.pathname
                                );


                            if (pathname === "/") {
                                pathname =
                                    "/WeatherGPT/index.html";
                            }


                            const requestedPath =
                                path.resolve(
                                    FRONTEND_ROOT,
                                    "." + pathname
                                );


                            if (
                                !requestedPath.startsWith(
                                    FRONTEND_ROOT
                                )
                            ) {

                                response.writeHead(
                                    403
                                );

                                response.end(
                                    "Forbidden"
                                );

                                return;
                            }


                            fs.stat(
                                requestedPath,
                                (error, stats) => {

                                    if (error) {

                                        response.writeHead(
                                            404,
                                            {
                                                "Content-Type":
                                                    "text/plain"
                                            }
                                        );

                                        response.end(
                                            "File not found"
                                        );

                                        return;
                                    }


                                    if (!stats.isFile()) {

                                        response.writeHead(
                                            404
                                        );

                                        response.end(
                                            "Not a file"
                                        );

                                        return;
                                    }


                                    response.writeHead(
                                        200,
                                        {
                                            "Content-Type":
                                                getContentType(
                                                    requestedPath
                                                ),
                                            "Cache-Control":
                                                "no-store"
                                        }
                                    );


                                    fs.createReadStream(
                                        requestedPath
                                    ).pipe(
                                        response
                                    );
                                }
                            );

                        } catch (error) {

                            console.error(
                                "Static server error:",
                                error
                            );

                            response.writeHead(
                                500
                            );

                            response.end(
                                "Internal server error"
                            );
                        }
                    }
                );


            server.listen(
                PORT,
                HOST,
                () => {

                    console.log(
                        `Vaayu frontend server running at http://${HOST}:${PORT}`
                    );

                    resolve(server);
                }
            );


            server.on(
                "error",
                reject
            );
        }
    );
}


async function createWindow() {

    const frontendServer =
        await startFrontendServer();


    const window =
        new BrowserWindow({

            width: 1440,

            height: 900,

            minWidth: 1100,

            minHeight: 700,

            show: false,

            title: "Vaayu",

            backgroundColor: "#eef5fb",

            webPreferences: {

                nodeIntegration: false,

                contextIsolation: true,

                sandbox: true,

                devTools: true
            }
        });


    window.once(
        "ready-to-show",
        () => {

            window.show();

        }
    );


    await window.loadURL(
        `http://${HOST}:${PORT}/WeatherGPT/index.html`
    );


    window.on(
        "closed",
        () => {

            frontendServer.close();

        }
    );
}


app.whenReady().then(
    async () => {

        try {

            await createWindow();

        } catch (error) {

            console.error(
                "Unable to start Vaayu:",
                error
            );

            app.quit();
        }


        app.on(
            "activate",
            async () => {

                if (
                    BrowserWindow
                        .getAllWindows()
                        .length === 0
                ) {

                    await createWindow();
                }
            }
        );
    }
);


app.on(
    "window-all-closed",
    () => {

        if (
            process.platform !== "darwin"
        ) {

            app.quit();
        }
    }
);