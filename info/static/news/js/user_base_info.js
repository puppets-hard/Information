function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

// 获取性别的值
function getRadio() {
    var obj = document.getElementsByName("gender");
    for(var i=0; i<obj.length; i ++){
        if(obj[i].checked){
            // alert(obj[i].value);
            return obj[i].value;
        }
    }
}


$(function () {

    $(".base_info").submit(function (e) {
        e.preventDefault()

        var signature = $("#signature").val()
        var nick_name = $("#nick_name").val()
        var gender = getRadio()
        console.info(gender)

        if (!nick_name) {
            alert('请输入昵称')
            return
        }
        if (!gender) {
            alert('请选择性别')
        }

        var params = {
            "signature": signature,
            "nick_name": nick_name,
            "gender": gender
        }

        // TODO 修改用户信息接口
        $.ajax({
            url: "/user/base_info",
            type: "post",
            contentType: "application/json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            data: JSON.stringify(params),
            success: function(resp){
                if (resp.errno == "0"){
                    $('.user_center_name', parent.document).html(params['nick_name'])
                    $('#nick_name', parent.document).html(params['nick_name'])
                    $('.input_sub').blur()


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