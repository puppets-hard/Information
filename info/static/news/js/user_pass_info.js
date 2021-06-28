function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}


$(function () {
    $(".pass_info").submit(function (e) {
        e.preventDefault()
        // alert("1")


        var params = {}

        console.info($(this).serializeArray())  // 返回一个对象，包含对象的name和value
        $(this).serializeArray().map(function (x) {
            params[x.name] = x.value;  // 遍历出对象的name和value，放到params中
        });


        var new_password = params["new_password"];
        var new_password2 = params["new_password2"];

        if (new_password != new_password2){
            alert("两次输入的密码不一致")
            return
        }



        // TODO 修改密码
        $.ajax({
            url: "/user/password_info",
            type: "post",
            contentType: "application/json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            data: JSON.stringify(params),
            success: function (resp) {
                if (resp.errno == "0"){
                    alert("修改成功！")
                    window.location.reload()
                }
                else{
                    alert(resp.errmsg)
                }
            },
            error: function () {
                alert("error!")
            }

        })
    })
})