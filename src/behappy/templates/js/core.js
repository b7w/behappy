var core = {
    shadowbox: function () {
        var isMobile = window.matchMedia('only screen and (max-width: 480px)').matches;
        // The trick for jQuery.delegate
        if (/ip(hone|od)|ipad/i.test(navigator.userAgent)) {
            jQuery("body").css("cursor", "pointer");
        }

        link2id = function (item) {
            return jQuery(item).parent().parent().attr('id')
        };

        if (isMobile) {
            jQuery('.shadowbox').bind('click', function (e) {
                e.preventDefault();
            });
            if (window.location.hash !== '') {
                var id = window.location.hash.substr(2);
                jQuery('html, body').animate({ scrollTop: jQuery('#' + id).offset().top - 32 }, 500);
            }
        } else {
            var settings = {
                overlayOpacity: 0.95,
                slideshowDelay: 4,
                viewportPadding: 12,
                onOpen: function (item) {
                    window.location.hash = '#!' + link2id(item.link);
                    Shadowbox.play();
                    Shadowbox.pause();
                },
                onChange: function (item) {
                    window.location.hash = '#!' + link2id(item.link);
                },
                onClose: function (item) {
                    window.location.hash = '#!';
                }
            };
            Shadowbox.init(settings);

            var show_image = function () {
                if (window.location.hash !== '') {
                    var id = window.location.hash.substr(2);
                    var a = jQuery('#' + id).find('a.shadowbox')[0];
                    if (typeof(a) !== "undefined") {
                        for (i in Shadowbox.cache) {
                            var item = Shadowbox.cache[i];
                            if (item.link.href === a.href) {
                                Shadowbox.open(item);
                                break;
                            }
                        }
                    }
                }
            };
            // Fucking Shadowbox.init callback doesn't work
            setTimeout(show_image, 1000);

            jQuery('body').delegate('#sb-body', 'click', function (e) {
                var width = jQuery(this).width() / 3;
                var x = e.pageX - jQuery(this).offset().left;
                if (x < width) {
                    Shadowbox.previous()
                } else {
                    Shadowbox.next();
                }
            });
        }
    },

    imageLoading: function () {
        var isMobile = window.matchMedia('only screen and (max-width: 480px)').matches;

        function load() {
            var height = jQuery(window).scrollTop() + jQuery(window).height();
            if (isMobile)
                height = height + jQuery(window).height();
            else
                height = height + jQuery(window).height() / 2;

            jQuery('.album img[data-src]').each(function (i, img) {
                var image = jQuery(img);
                if (image.offset().top < height) {
                    image.attr('src', image.attr('data-src'));
                    image.removeAttr('data-src');
                }
            });
        }

        load();

        jQuery(window).scroll(function () {
            load();
        });

        jQuery('.preview img').bind('load', function () {
            jQuery(this).css({opacity: 1});
        });
    },

    initCSRF: function () {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        function csrfSafeMethod(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        jQuery.ajaxSetup({
            crossDomain: false, // obviates need for sameOrigin test
            beforeSend: function (xhr, settings) {
                var csrftoken = getCookie('csrftoken');
                if (!csrfSafeMethod(settings.type)) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            }
        });
    }
};
