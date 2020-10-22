function theme_toggle() {
    const htmlTag = document.getElementsByTagName('html')[0]
    if (htmlTag.hasAttribute('data-theme')) {
        htmlTag.classList.remove("theme-dark");
        htmlTag.classList.add("theme-light");

        htmlTag.removeAttribute('data-theme')
        return window.localStorage.removeItem("site-theme")
    }

    console.log("toggle");

    htmlTag.classList.remove("theme-light");
    htmlTag.classList.add("theme-dark");

    htmlTag.setAttribute('data-theme', 'dark')
    window.localStorage.setItem("site-theme", "dark")
}

function theme_init () {
    var theme = window.localStorage.getItem("site-theme")
    const htmlTag = document.getElementsByTagName("html")[0]
    if (theme !== null) {
        htmlTag.setAttribute("data-theme", theme)

        htmlTag.classList.remove("theme-dark");
        htmlTag.classList.remove("theme-light");
    } else {
        theme = "light";
    }
    console.log(theme);
    htmlTag.classList.add("theme-" + theme);
}
theme_init();

window.addEventListener('load', function() {
    document
        .getElementById("theme-toggle")
        .addEventListener("click", theme_toggle);
});
